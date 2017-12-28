from pamagent.trace import DatabaseTrace, register_database_client, FunctionTrace
from pamagent.transaction_cache import current_transaction
from pamagent.wrapper import wrap_object, _WrapperBase, callable_name

DEFAULT = object()


class CursorWrapper(_WrapperBase):

    def __init__(self, cursor, dbapi2_module, connect_params, cursor_params):
        super(CursorWrapper, self).__init__(cursor)
        self._pam_dbapi2_module = dbapi2_module
        self._pam_connect_params = connect_params
        self._pam_cursor_params = cursor_params

    def execute(self, sql, parameters=DEFAULT, *args, **kwargs):
        transaction = current_transaction()
        if parameters is not DEFAULT:
            with DatabaseTrace(transaction, sql, self._pam_dbapi2_module, self._pam_connect_params,
                               self._pam_cursor_params, sql_parameters=parameters,
                               host=self._pam_connect_params[1].get('host'),
                               port=self._pam_connect_params[1].get('port')):
                return self.__wrapped__.execute(sql, parameters, *args, **kwargs)
        else:
            with DatabaseTrace(transaction, sql, self._pam_dbapi2_module, self._pam_connect_params,
                               self._pam_cursor_params, host=self._pam_connect_params[1].get('host'),
                               port=self._pam_connect_params[1].get('port')):
                return self.__wrapped__.execute(sql, **kwargs)

    def executemany(self, sql, seq_of_parameters):
        transaction = current_transaction()
        try:
            parameters = seq_of_parameters[0]
        except (TypeError, IndexError):
            parameters = DEFAULT
        if parameters is not DEFAULT:
            with DatabaseTrace(transaction, sql, self._pam_dbapi2_module, self._pam_connect_params,
                               self._pam_cursor_params, parameters):
                return self.__wrapped__.executemany(sql, seq_of_parameters)
        else:
            with DatabaseTrace(transaction, sql, self._pam_dbapi2_module, self._pam_connect_params,
                               self._pam_cursor_params):
                return self.__wrapped__.executemany(sql, seq_of_parameters)

    def callproc(self, procname, parameters=DEFAULT):
        transaction = current_transaction()
        with DatabaseTrace(transaction, 'CALL %s' % procname, self._pam_dbapi2_module, self._pam_connect_params):
            if parameters is not DEFAULT:
                return self.__wrapped__.callproc(procname, parameters)
            else:
                return self.__wrapped__.callproc(procname)


class ConnectionWrapper(_WrapperBase):
    __cursor_wrapper__ = CursorWrapper

    def __init__(self, connection, dbapi2_module, connect_params):
        super(ConnectionWrapper, self).__init__(connection)
        self._pam_dbapi2_module = dbapi2_module
        self._pam_connect_params = connect_params

    def cursor(self, *args, **kwargs):
        return self.__cursor_wrapper__(self.__wrapped__.cursor(*args, **kwargs), self._pam_dbapi2_module,
                                       self._pam_connect_params, (args, kwargs))

    def commit(self):
        transaction = current_transaction()
        with DatabaseTrace(transaction, 'COMMIT', self._pam_dbapi2_module,
                           database_name=self._pam_connect_params[1]['database'],
                           host=self._pam_connect_params[1].get('host'), port=self._pam_connect_params[1].get('port')):
            return self.__wrapped__.commit()

    def rollback(self):
        transaction = current_transaction()
        with DatabaseTrace(transaction, 'ROLLBACK', self._pam_dbapi2_module, self._pam_connect_params,
                           database_name=self._pam_connect_params[1]['database'],
                           host=self._pam_connect_params[1].get('host'), port=self._pam_connect_params[1].get('port')):
            return self.__wrapped__.rollback()


class ConnectionFactory(_WrapperBase):
    __connection_wrapper__ = ConnectionWrapper

    def __init__(self, connect, dbapi2_module):
        super(ConnectionFactory, self).__init__(connect)
        self._pam_dbapi2_module = dbapi2_module

    def __call__(self, *args, **kwargs):
        transaction = current_transaction()
        with FunctionTrace(transaction, callable_name(self.__wrapped__)):
            return self.__connection_wrapper__(self.__wrapped__(*args, **kwargs), self._pam_dbapi2_module,
                                               (args, kwargs))


def instrument(module):
    register_database_client(module, 'DBAPI2', 'single')
    wrap_object(module, 'connect', ConnectionFactory, (module,))
