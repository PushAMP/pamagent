from pamagent.hooks import requests_hook, django_hook
from pamagent import pamagent_core


def _init_builtin() -> None:
        requests_hook.patch()
        django_hook.patch()


def init(collector_host: str="pamcollector.pushamp.com")->None:
    _init_builtin()
    pamagent_core.activate(collector_host)
