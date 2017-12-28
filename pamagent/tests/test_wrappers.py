import os

from django.conf import settings, global_settings
from django.core.handlers.wsgi import WSGIHandler
from django.test import RequestFactory

import wrapt

from pamagent.hooks.requests_hook import instrument_requests_sessions, instrument_requests_api
from pamagent.hooks.django_hook import instrument_django_core_handlers_wsgi
from pamagent.transaction import Transaction
from pamagent.agent import init
from pamagent.wrapper import FuncWrapper
from pamagent.hooks.sqlite_hook import ConnectionFactory as SqliteConnectionFactory
from pamagent.hooks.psycopg2_hook import ConnectionFactory as PGConectionFactory


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


def test_request_request():
    wrapt.register_post_import_hook(instrument_requests_api, 'requests.api')
    import requests
    tr = Transaction(enabled=True)
    tr.set_transaction_path("/yt")
    with tr:
        requests.get("http://ya.ru/?key=val&ke1=val1")
        requests.post("http://ya.ru")


def test_django_wrap():
    wrapt.register_post_import_hook(instrument_django_core_handlers_wsgi,  'django.core.handlers.wsgi')
    wrapt.register_post_import_hook(instrument_requests_sessions, 'requests')
    environ = RequestFactory().get('/').environ
    handler = WSGIHandler()
    response = handler(environ, lambda *a, **k: None)
    assert response.status_code == 200


def test_hooks():
    init(token="qwerty")
    import requests
    assert type(requests.api.request) == FuncWrapper


def test_sqlite_hooks():
    init(token="qwerty")
    import sqlite3
    assert type(sqlite3.connect) == SqliteConnectionFactory
    tr = Transaction(enabled=True)
    tr.set_transaction_path("/yt")
    with tr:
        conn = sqlite3.connect('example.db')

        c = conn.cursor()
        c.execute('''CREATE TABLE stocks
                     (date TEXT, trans TEXT, symbol TEXT, qty REAL, price REAL)''')

        c.execute("INSERT INTO stocks VALUES ('2006-01-05','BUY','RHAT',100,35.14)")
        conn.commit()
        c.execute("SELECT * FROM stocks WHERE symbol='RHAT'")
        print(c.fetchone())
        conn.close()
        print(tr.dump())
    os.remove('example.db')


def test_psycopg2_hooks():
    init(token="qwerty")
    import psycopg2
    assert type(psycopg2.connect) == PGConectionFactory
    tr = Transaction(enabled=True)
    tr.set_transaction_path("/yt")
    with tr:
        conn = psycopg2.connect(database="test_db", user="test", password="test", host="127.0.0.1")
        c = conn.cursor()
        c.execute("INSERT INTO stocks VALUES ('2006-01-05','BUY','RHAT',100,35.14)")
        conn.commit()
        c.execute("SELECT * FROM stocks WHERE symbol='RHAT'")
        print(c.fetchone())
        conn.close()
        print(tr.dump())
