import wrapt

from pamagent.hooks.dbapi2 import (CursorWrapper as DBAPI2CursorWrapper, ConnectionWrapper as DBAPI2ConnectionWrapper,
                                   ConnectionFactory as DBAPI2ConnectionFactory)
from pamagent.trace import register_database_client, DatabaseTrace
from pamagent.transaction_cache import current_transaction
from pamagent.wrapper import FuncWrapper, callable_name, wrap_object


DEFAULT = object()


class CursorWrapper(DBAPI2CursorWrapper):
    def execute(self, sql, parameters=DEFAULT, *args, **kwargs):
        transaction = current_transaction()
        if parameters is not DEFAULT:
            with DatabaseTrace(transaction, sql, self._pam_dbapi2_module, self._pam_connect_params,
                               self._pam_cursor_params, parameters, (args, kwargs)):
                return self.__wrapped__.execute(sql, parameters, *args, **kwargs)
        else:
            with DatabaseTrace(transaction, sql, self._pam_dbapi2_module, self._pam_connect_params,
                               self._pam_cursor_params, None, (args, kwargs),
                               database_name=self._pam_connect_params[0][0]):
                return self.__wrapped__.execute(sql, **kwargs)

    def executescript(self, sql_script):
        transaction = current_transaction()
        with DatabaseTrace(transaction, sql_script, self._pam_dbapi2_module, self._pam_connect_params,
                           database_name=self._pam_connect_params[0]):
            return self.__wrapped__.executescript(sql_script)


class ConnectionWrapper(DBAPI2ConnectionWrapper):
    __cursor_wrapper__ = CursorWrapper

    def __enter__(self):
        transaction = current_transaction()
        name = callable_name(self.__wrapped__.__enter__)
        with FuncWrapper(transaction, name):
            self.__wrapped__.__enter__()
        return self

    def __exit__(self, exc, value, tb, *args, **kwargs):
        transaction = current_transaction()
        name = callable_name(self.__wrapped__.__exit__)
        with FuncWrapper(transaction, name):
            if exc is None and value is None and tb is None:
                with DatabaseTrace(transaction, 'COMMIT', self._pam_dbapi2_module, self._pam_connect_params):
                    return self.__wrapped__.__exit__(exc, value, tb)
            else:
                with DatabaseTrace(transaction, 'ROLLBACK', self._pam_dbapi2_module, self._pam_connect_params):
                    return self.__wrapped__.__exit__(exc, value, tb)

    def execute(self, sql, parameters=DEFAULT):
        transaction = current_transaction()
        if parameters is not DEFAULT:
            with DatabaseTrace(transaction, sql, self._pam_dbapi2_module, self._pam_connect_params,
                               database_name=self._pam_connect_params[0]):
                return self.__wrapped__.execute(sql, parameters)
        else:
            with DatabaseTrace(transaction, sql, self._pam_dbapi2_module, self._pam_connect_params,
                               database_name=self._pam_connect_params[0]):
                return self.__wrapped__.execute(sql)

    def executemany(self, sql, seq_of_parameters):
        transaction = current_transaction()
        with DatabaseTrace(transaction, sql, self._pam_dbapi2_module, self._pam_connect_params,
                           database_name=self._pam_connect_params[0]):
            return self.__wrapped__.executemany(sql, seq_of_parameters)

    def executescript(self, sql_script):
        transaction = current_transaction()
        with DatabaseTrace(transaction, sql_script, self._pam_dbapi2_module, self._pam_connect_params,
                           database_name=self._pam_connect_params[0]):
            return self.__wrapped__.executescript(sql_script)

    def commit(self):
        transaction = current_transaction()
        with DatabaseTrace(transaction, 'COMMIT', self._pam_dbapi2_module,
                           database_name=self._pam_connect_params[0][0]):
            return self.__wrapped__.commit()

    def rollback(self):
        transaction = current_transaction()
        with DatabaseTrace(transaction, 'ROLLBACK', self._pam_dbapi2_module, self._pam_connect_params,
                           database_name=self._pam_connect_params[0]):
            return self.__wrapped__.rollback()


class ConnectionFactory(DBAPI2ConnectionFactory):
    __connection_wrapper__ = ConnectionWrapper


def instance_info(args, kwargs):
    def _bind_params(database_name, *args, **kwargs):
        return database_name

    database = _bind_params(*args, **kwargs)
    host = 'localhost'
    port = None

    return host, port, database


def instrument_sqlite3_dbapi2(module):
    register_database_client(module, 'SQLite', 'single', instance_info=instance_info)
    wrap_object(module, 'connect', ConnectionFactory, (module,))


def instrument_sqlite3(module):
    if not isinstance(module.connect, ConnectionFactory):
        register_database_client(module, 'SQLite', instance_info=instance_info)
        wrap_object(module, 'connect', ConnectionFactory, (module,))


def patch():
    wrapt.register_post_import_hook(instrument_sqlite3, 'sqlite3')
    wrapt.register_post_import_hook(instrument_sqlite3_dbapi2, 'sqlite3.dbapi2')
