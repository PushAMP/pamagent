from pamagent.hooks import requests_hook, django_hook, sqlite_hook, psycopg2_hook, mysql_hook
from pamagent import pamagent_core


def _init_builtin() -> None:
        requests_hook.patch()
        django_hook.patch()
        sqlite_hook.patch()
        psycopg2_hook.patch()
        mysql_hook.patch()


def init(token: str, collector_host: str="pamcollector.pushamp.com") -> None:
    _init_builtin()
    pamagent_core.activate(token, collector_host)
