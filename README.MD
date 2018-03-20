[![Codacy Badge](https://api.codacy.com/project/badge/Grade/1ccab8e3c42a441498a2f335a560a471)](https://www.codacy.com/app/zaabjuda/pamagent?utm_source=github.com&utm_medium=referral&utm_content=PushAMP/pamagent&utm_campaign=badger)
[![Build Status](https://travis-ci.org/PushAMP/pamagent.svg?branch=master)](https://travis-ci.org/PushAMP/pamagent)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/pamagent.svg)](https://pypi.python.org/pypi/pamagent/)
[![PyPI version](https://badge.fury.io/py/pamagent.svg)](https://badge.fury.io/py/pamagent)
[![Latest Docs](https://img.shields.io/badge/Latest-Docs-1abc9c.svg)](https://pushamp.github.io/pamagent/)

pamagent
========

This is a Python Agent for PAM platform. See
[doc](https://pushamp.github.io/pamagent/) for more information

How-to install
==============

Linux 64-bit
------------
    pip install pamagent
Other OS
--------
1. Install *rust-nightly* via [rustup](https://www.rustup.rs)
2. pip install --no-binary :all: pamagent


Support technology
------------------
* Framaworks
  * Django
* Database(Drivers)
  * mysql-connector-python
  * mysqlclient
  * psycopg2
  * sqlite (builtin)
* Library for external call
  * requests
* Caches
  * Redis (redis-py)

TODO
----
* Tornado
* AsyncIO
* Asyncio-http
* cx_oracle
* urllib
* memcache
* flask
* twisted
* Django Templates
* Jinja2


How-to setup your app
=====================

Django
------
For django project you need include call agent.init in your wsgi.py file
For example, you would have:
```python
import os

from django.core.wsgi import get_wsgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_app.settings")


def pam_enable():
    try:
        from pamagent import agent
        agent.init(token='YOU_OWN_TOKEN')
    except Exception as exc:
        print(exc)


pam_enable()

application = get_wsgi_application()
```

When using uWSGI you will need add specific options to the uwsgi config

For example:

```ini
#test_app_uwsgi.ini
[uwsgi]
chdir           = /Users/dzhiltsov/Development/test_app
module          = test_app.wsgi
home            = /Users/dzhiltsov/Development/envs/test_app
http-socket = :9999
master          = true
processes       = 4
socket          = 127.0.0.1:8002
vacuum          = true
pp              = /Users/dzhiltsov/Development/envs/test_app
virtualenv = /Users/dzhiltsov/Development/envs/test_app
# Use this option and restrict yourself to a single web application
# per process
single-interpreter = true
# This option need if you use uwsgi<= 2.0.14
#wsgi-env-behavior = holy
# This option need if you use  option master=true
lazy-apps = true
# Custom option for configuring pamagent log level
env = PAMAGENT_LEVEL_LOG=2
```

