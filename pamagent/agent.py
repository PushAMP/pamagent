from pamagent.hooks import requests_hook, django_hook


def _init_builtin():
        requests_hook.patch()
        django_hook.patch()


def init():
    _init_builtin()
