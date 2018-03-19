import logging
from itertools import count

from pamagent.hooks import requests_hook, django_hook, sqlite_hook, psycopg2_hook, mysql_hook, redis_hook
from pamagent import pamagent_core

_logger = logging.getLogger(__name__)


def _init_builtin() -> None:
        requests_hook.patch()
        django_hook.patch()
        sqlite_hook.patch()
        psycopg2_hook.patch()
        mysql_hook.patch()
        redis_hook.path()


def init(token: str, collector_host: str="pamcollector.pushamp.com", _count=count()) -> None:
    if next(_count):
        _logger.warning("The PamAgent The was already initialized and activate")
        return
    _init_builtin()
    pamagent_core.activate(token, collector_host)
