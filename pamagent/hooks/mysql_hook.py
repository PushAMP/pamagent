import wrapt

from pamagent.hooks.dbapi2 import (ConnectionWrapper as DBAPI2ConnectionWrapper,
                                   ConnectionFactory as DBAPI2ConnectionFactory)
from pamagent.trace import register_database_client
from pamagent.transaction_cache import current_transaction
from pamagent.wrapper import FuncWrapper, callable_name, wrap_object


class ConnectionWrapper(DBAPI2ConnectionWrapper):
    def __enter__(self):
        transaction = current_transaction()
        name = callable_name(self.__wrapped__.__enter__)
        with FuncWrapper(transaction, name):
            cursor = self.__wrapped__.__enter__()
        return self.__cursor_wrapper__(cursor, self._pam_dbapi2_module, self._pam_connect_params, None)


class ConnectionFactory(DBAPI2ConnectionFactory):
    __connection_wrapper__ = ConnectionWrapper


def _instance_info(_, kwargs):
    host = kwargs.get('host')
    port = kwargs.get('port')
    db = kwargs.get('db')
    return host, port, db


def instrument_mysql(module):
    register_database_client(module, database_product='MySQL', quoting_style='single+double',
                             instance_info=_instance_info)

    wrap_object(module, 'connect', ConnectionFactory, (module,))
    if hasattr(module, 'Connect'):
        wrap_object(module, 'Connect', ConnectionFactory, (module,))


def patch():
    for module in ['mysql.connector', 'MySQLdb']:
        wrapt.register_post_import_hook(instrument_mysql, module)
