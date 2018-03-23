import os

import wrapt

from pamagent.hooks.requests_hook import instrument_requests_sessions, instrument_requests_api
from pamagent.transaction import Transaction
from pamagent.agent import init
from pamagent.wrapper import FuncWrapper
from pamagent.hooks.sqlite_hook import ConnectionFactory as SqliteConnectionFactory
from pamagent.hooks.psycopg2_hook import ConnectionFactory as PGConnectionFactory
from pamagent.hooks.mysql_hook import ConnectionFactory as MySqlConnectionFactory


init(token="qwerty")


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
    from django.conf import settings, global_settings
    from django.core.handlers.wsgi import WSGIHandler
    from django.test import RequestFactory
    global_settings.ROOT_URLCONF = "pamagent.tests.urls"
    global_settings.ALLOWED_HOSTS = ["*"]
    settings.configure()

    environ = RequestFactory().get('/').environ
    handler = WSGIHandler()
    response = handler(environ, lambda *a, **k: None)
    assert response.status_code == 200


def test_hooks():
    import requests
    assert type(requests.api.request) == FuncWrapper


def test_sqlite_hooks():
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
    import psycopg2
    assert type(psycopg2.connect) == PGConnectionFactory
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


def test_mysql_connector_hooks():
    import mysql.connector
    assert type(mysql.connector.connect) == MySqlConnectionFactory
    tr = Transaction(enabled=True)
    tr.set_transaction_path("/yt")
    with tr:
        conn = mysql.connector.connect(database="test_db", user="test", password="test", host="127.0.0.1")
        c = conn.cursor()
        c.execute("INSERT INTO stocks VALUES ('2006-01-05','BUY','RHAT',100,35.14)")
        conn.commit()
        c.execute("SELECT * FROM stocks WHERE symbol='RHAT'")
        print(c.fetchone())
        conn.close()
        print(tr.dump())


def test_mysqldb_hooks():
    import MySQLdb
    assert type(MySQLdb.connect) == MySqlConnectionFactory
    tr = Transaction(enabled=True)
    tr.set_transaction_path("/yt")
    with tr:
        conn = MySQLdb.connect(database="test_db", user="test", password="test", host="127.0.0.1")
        c = conn.cursor()
        c.execute("INSERT INTO stocks VALUES ('2006-01-05','BUY','RHAT',100,35.14)")
        conn.commit()
        c.execute("SELECT * FROM stocks WHERE symbol='RHAT'")
        print(c.fetchone())
        conn.close()
        print(tr.dump())


def test_redis_hooks():
    import redis
    pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
    red = redis.Redis(connection_pool=pool)
    tr = Transaction(enabled=True)
    tr.set_transaction_path("/yt")
    with tr:
        red.get("Fed")
        red.set("Fed", 1)
        red.get("Fed")
        print(tr.dump())
