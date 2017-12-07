import logging
import functools
import time
from typing import Optional

from pamagent import pamagent_core

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


def register_database_client(dbapi2_module, database_product, quoting_style='single', explain_query=None,
                             explain_stmts=[], instance_info=None):
    _logger.debug('Registering database client module %r where database '
                  'is %r, quoting style is %r, explain query statement is %r and '
                  'the SQL statements on which explain plans can be run are %r.',
                  dbapi2_module, database_product, quoting_style, explain_query,
                  explain_stmts)

    dbapi2_module._pm_database_product = database_product
    dbapi2_module._pm_quoting_style = quoting_style
    dbapi2_module._pm_explain_query = explain_query
    dbapi2_module._pm_explain_stmts = explain_stmts
    dbapi2_module._pm_instance_info = instance_info
    dbapi2_module._pm_datastore_instance_feature_flag = False


class DatabaseTrace(TimeTrace):
    __async_explain_plan_logged = False

    def __init__(self, transaction, sql, dbapi2_module=None, connect_params=None, cursor_params=None,
                 sql_parameters=None, execute_params=None, host=None, port_path_or_id=None, database_name=None):

        super(DatabaseTrace, self).__init__(transaction)

        self.sql = sql

        self.dbapi2_module = dbapi2_module

        self.connect_params = connect_params
        self.cursor_params = cursor_params
        self.sql_parameters = sql_parameters
        self.execute_params = execute_params
        self.host = host
        self.port_path_or_id = port_path_or_id
        self.database_name = database_name

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, dict(
            sql=self.sql, dbapi2_module=self.dbapi2_module))

    @property
    def is_async_mode(self):
        # Check for `async=1` keyword argument in connect_params, which
        # indicates that psycopg2 driver is being used in async mode.

        try:
            _, kwargs = self.connect_params
        except TypeError:
            return False
        else:
            return 'async' in kwargs and kwargs['async']

    def _log_async_warning(self):
        # Only log the warning the first time.

        if not DatabaseTrace.__async_explain_plan_logged:
            DatabaseTrace.__async_explain_plan_logged = True
            _logger.warning('Explain plans are not supported for queries '
                            'made over database connections in asynchronous mode.')

    def finalize_data(self, transaction, exc=None, value=None, tb=None):
        self.stack_trace = None

        connect_params = None
        cursor_params = None
        sql_parameters = None
        execute_params = None
        host = None
        port_path_or_id = None
        database_name = None

        agent_limits = 100

        if self.dbapi2_module and self.connect_params and self.dbapi2_module._pm_instance_info is not None:
            instance_info = self.dbapi2_module._pm_instance_info(*self.connect_params)

            host, port_path_or_id, _ = instance_info

            _, _, database_name = instance_info

        if self.is_async_mode:
            self._log_async_warning()
        else:
            # Only remember all the params for the calls if know
            # there is a chance we will need to do an explain
            # plan. We never allow an explain plan to be done if
            # an exception occurred in doing the query in case
            # doing the explain plan with the same inputs could
            # cause further problems.

            if exc is None and not self.is_async_mode and self.duration >= 1000 and self.connect_params is not None:
                if transaction._explain_plan_count < agent_limits.sql_explain_plans:
                    connect_params = self.connect_params
                    cursor_params = self.cursor_params
                    sql_parameters = self.sql_parameters
                    execute_params = self.execute_params
                    transaction._explain_plan_count += 1

        self.connect_params = connect_params
        self.cursor_params = cursor_params
        self.sql_parameters = sql_parameters
        self.execute_params = execute_params
        self.host = host
        self.port_path_or_id = port_path_or_id
        self.database_name = database_name

    def terminal_node(self):
        return True


def DatabaseTraceWrapper(wrapped, sql, dbapi2_module=None):
    def _pm_database_trace_wrapper_(wrapped, instance, args, kwargs):
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

    return FuncWrapper(wrapped, _pm_database_trace_wrapper_)


def database_trace(sql, dbapi2_module=None):
    return functools.partial(DatabaseTraceWrapper, sql=sql, dbapi2_module=dbapi2_module)


def wrap_database_trace(module, object_path, sql, dbapi2_module=None):
    wrap_object(module, object_path, DatabaseTraceWrapper, (sql, dbapi2_module))
