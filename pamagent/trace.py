import logging
import functools
import time
from typing import Optional

from pamagent import pamagent_core
from pamagent.utils.sql_statement import sql_statement

from .wrapper import FuncWrapper, wrap_object
from .transaction_cache import current_transaction

_logger = logging.getLogger(__name__)


class TimeTrace(object):
    node = None

    def __init__(self, transaction: int):
        self.transaction = transaction
        self.children = []
        self.start_time = 0.0
        self.end_time = 0.0
        self.duration = 0.0
        self.exclusive = 0.0
        self.activated = False

    def __enter__(self):
        if not self.transaction:
            return self
        pamagent_core.push_current(self.transaction, id(self), time.time())
        self.activated = True
        return self

    def __exit__(self, exc, value, tb):
        if not self.transaction:
            return
        if not self.activated:
            _logger.error('Runtime error. The __exit__() method was called prior to __enter__()')
            return
        transaction = self.transaction
        self.transaction = None
        self.end_time = time.time()
        pamagent_core.pop_current(transaction, id(self), self.end_time)


class FunctionTrace(TimeTrace):
    def __init__(self, transaction: int, func_name: str, name: str = None):
        super(FunctionTrace, self).__init__(transaction)
        self.name = name or func_name
        self.func_name = func_name

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, dict(name=self.name, func_name=self.func_name))

    def __enter__(self):
        if not self.transaction:
            return self
        pamagent_core.push_current(self.transaction, id(self), time.time(), func_name=self.func_name)
        self.activated = True
        return self


class ExternalTrace(TimeTrace):
    def __init__(self, transaction: int, library: str, url: str, method: Optional[str] = None):
        super(ExternalTrace, self).__init__(transaction)
        self.library = library
        self.url = url
        self.method = method
        self.params = {}

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, dict(
            library=self.library, url=self.url, method=self.method))

    def __enter__(self):
        if not self.transaction:
            return self
        pamagent_core.push_current_external(self.transaction, id(self), time.time(), self.url, self.library,
                                            self.method)
        self.activated = True
        return self


class DatabaseTrace(TimeTrace):
    __slots__ = ['sql', 'dbapi2_module', 'connect_params', 'cursor_params', 'sql_parameters', 'execute_params', 'host',
                 'port', 'database_name', '_sql_statement']

    def __init__(self, transaction, sql, dbapi2_module=None, connect_params=None, cursor_params=None,
                 sql_parameters=None, execute_params=None, host=None, port=None, database_name=None):
        super(DatabaseTrace, self).__init__(transaction)

        self.sql = sql

        self.dbapi2_module = dbapi2_module

        self.connect_params = connect_params
        self.cursor_params = cursor_params
        self.sql_parameters = sql_parameters
        self.execute_params = execute_params
        self.host = host
        self.port = port
        self.database_name = database_name or connect_params[1].get('database')
        self._sql_statement = sql_statement(self.sql, self.dbapi2_module)

    def _operation(self):
        return self._sql_statement.operation

    def _target(self):
        return self._sql_statement.target

    def _obfuse(self):
        return self._sql_statement.obfuscated

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, dict(
            sql=self.sql, dbapi2_module=self.dbapi2_module))

    def __enter__(self):
        if not self.transaction:
            return self
        pamagent_core.push_current_database(self.transaction, id(self), time.time(),
                                            self.dbapi2_module[0]._pam_database_product, self.database_name, self.host,
                                            int(self.port or 0), self._operation(), self._target(), self._obfuse())
        self.activated = True
        return self


class CacheTrace(TimeTrace):
    def __init__(self, transaction, product, operation, host, port, db=0):
        self.product = product
        self.operation = operation
        self.host = host
        self.port = port
        self.db = db
        super(CacheTrace, self).__init__(transaction)

    def __enter__(self):
        if not self.transaction:
            return self
        pamagent_core.push_current_cache(self.transaction, id(self), time.time(), self.db, self.host, self.port,
                                         self.operation, self.product)
        self.activated = True
        return self

    def __exit__(self, exc, value, tb):
        if not self.transaction:
            return
        if not self.activated:
            _logger.error('Runtime error. The __exit__() method was called prior to __enter__()')
            return
        transaction = self.transaction
        self.transaction = None
        self.end_time = time.time()
        pamagent_core.pop_current(transaction, id(self), self.end_time)


def ExternalTraceWrapper(wrapped, library, url, method):
    def dynamic_wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        if callable(url):
            if instance is not None:
                _url = url(instance, *args, **kwargs)
            else:
                _url = url(*args, **kwargs)

        else:
            _url = url

        if callable(method):
            if instance is not None:
                _method = method(instance, *args, **kwargs)
            else:
                _method = method(*args, **kwargs)

        else:
            _method = method

        with ExternalTrace(transaction, library, _url, _method):
            return wrapped(*args, **kwargs)

    return FuncWrapper(wrapped, dynamic_wrapper)


def external_trace(library, url, method=None):
    return functools.partial(ExternalTraceWrapper, library=library, url=url, method=method)


def wrap_external_trace(module, object_path, library, url, method=None):
    wrap_object(module, object_path, ExternalTraceWrapper, library, url, method)


def register_database_client(dbapi2_module, database_product, quoting_style='single', instance_info=None):
    _logger.debug('Registering database client %r where database is %r, quoting style is %r.',
                  dbapi2_module, database_product, quoting_style)

    dbapi2_module._pam_database_product = database_product
    dbapi2_module._pam_quoting_style = quoting_style
    dbapi2_module._pam_instance_info = instance_info
    dbapi2_module._pam_datastore_instance_feature_flag = False


def DatabaseTraceWrapper(wrapped, sql, dbapi2_module=None):
    def _pam_database_trace_wrapper_(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        if callable(sql):
            if instance is not None:
                _sql = sql(instance, *args, **kwargs)
            else:
                _sql = sql(*args, **kwargs)
        else:
            _sql = sql

        with DatabaseTrace(transaction, _sql, dbapi2_module):
            return wrapped(*args, **kwargs)

    return FuncWrapper(wrapped, _pam_database_trace_wrapper_)


def database_trace(sql, dbapi2_module=None):
    return functools.partial(DatabaseTraceWrapper, sql=sql, dbapi2_module=dbapi2_module)


def wrap_database_trace(module, object_path, sql, dbapi2_module=None):
    wrap_object(module, object_path, DatabaseTraceWrapper, (sql, dbapi2_module))


def wrap_cache_trace(module, object_path, product, wrapper):
    wrap_object(module, object_path, wrapper, product)
