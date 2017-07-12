from django.conf import settings, global_settings
from django.core.handlers.wsgi import WSGIHandler
from django.test import RequestFactory

import wrapt

from pamagent.agent import instrument_requests_sessions, instrument_django_core_handlers_wsgi
from pamagent.transaction import Transaction


global_settings.ROOT_URLCONF = "pamagent.tests.urls"
global_settings.ALLOWED_HOSTS = ["*"]
settings.configure()


def test_request_wrap():
    instrument_requests_sessions("requests")
    import requests
    tr = Transaction(enabled=True)
    tr.set_transaction_path("/yt")
    with tr:
        s = requests.session()
        s.get("http://ya.ru")


def test_django_wrap():
    wrapt.register_post_import_hook(instrument_django_core_handlers_wsgi,
                                    'django.core.handlers.wsgi')
    wrapt.register_post_import_hook(instrument_requests_sessions, 'requests')
    environ = RequestFactory().get('/').environ
    handler = WSGIHandler()
    response = handler(environ, lambda *a, **k: None)
    assert response.status_code == 200
