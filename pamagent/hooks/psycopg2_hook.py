from urllib.parse import parse_qsl, unquote, urlparse

import wrapt

from pamagent.hooks.dbapi2 import (ConnectionWrapper as DBAPI2ConnectionWrapper,
                                   ConnectionFactory as DBAPI2ConnectionFactory)
from pamagent.trace import register_database_client, DatabaseTrace
from pamagent.transaction_cache import current_transaction
from pamagent.wrapper import FuncWrapper, callable_name, wrap_object, wrap_function_wrapper
from pamagent.wrapper import ObjectProxy

DEFAULT = object()


class ConnectionWrapper(DBAPI2ConnectionWrapper):
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
            if exc is None:
                with DatabaseTrace(transaction, 'COMMIT',
                                   self._pam_dbapi2_module, self._pam_connect_params):
                    return self.__wrapped__.__exit__(exc, value, tb)
            else:
                with DatabaseTrace(transaction, 'ROLLBACK',
                                   self._pam_dbapi2_module, self._pam_connect_params):
                    return self.__wrapped__.__exit__(exc, value, tb)


class ConnectionFactory(DBAPI2ConnectionFactory):
    __connection_wrapper__ = ConnectionWrapper


def _parse_connect_params(args, kwargs):
    def _bind_params(dsn=None, *_args, **_kwargs):
        return dsn

    dsn = _bind_params(*args, **kwargs)

    try:
        if dsn and (dsn.startswith('postgres://') or dsn.startswith('postgresql://')):
            parsed_uri = urlparse(dsn)

            host = parsed_uri.hostname or None
            host = host and unquote(host)
            port = parsed_uri.port

            db_name = parsed_uri.path
            db_name = db_name and db_name.lstrip('/')
            db_name = db_name or None

            query = parsed_uri.query or ''
            qp = dict(parse_qsl(query))

            host = qp.get('host') or host or None
            port = qp.get('port') or port
            db_name = qp.get('dbname') or db_name
        elif dsn:
            kv = dict([pair.split('=', 2) for pair in dsn.split()])
            host = kv.get('host')
            port = kv.get('port')
            db_name = kv.get('dbname')
        else:
            host = kwargs.get('host')
            port = kwargs.get('port')
            db_name = kwargs.get('database')
        host, port, db_name = [str(s) if s is not None else s for s in (host, port, db_name)]
    except Exception:
        host = 'localhost'
        port = 5432
        db_name = 'unknown'

    return host, port, db_name


def instance_info(args, kwargs):
    host, port, db_name = _parse_connect_params(args, kwargs)
    return host, port, db_name


def wrapper_psycopg2_register_type(wrapped, _instance, args, kwargs):
    def _bind_params(bind_obj, bind_scope=None):
        return bind_obj, bind_scope

    obj, scope = _bind_params(*args, **kwargs)

    if isinstance(scope, ObjectProxy):
        scope = scope.__wrapped__

    if scope is not None:
        return wrapped(obj, scope)
    else:
        return wrapped(obj)


def instrument_psycopg2(module):
    register_database_client(module, 'PostgreSQL', instance_info=instance_info)
    wrap_object(module, 'connect', ConnectionFactory, (module,))


def instrument_psycopg2_psycopg2(module):
    if hasattr(module, 'register_type'):
        if not isinstance(module.register_type, ObjectProxy):
            wrap_function_wrapper(module, 'register_type', wrapper_psycopg2_register_type)


def patch():
    wrapt.register_post_import_hook(instrument_psycopg2, 'psycopg2')
    wrapt.register_post_import_hook(instrument_psycopg2_psycopg2, 'psycopg2._psycopg2')
