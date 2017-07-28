import logging
import functools
import time
from typing import Optional

from pamagent import pamagent_core

from .wrapper import FuncWrapper, wrap_object
from .transaction_cache import current_transaction


_logger = logging.getLogger(__name__)


class TimeTrace(object):
    node = None

    def __init__(self, transaction: int):
        self.transaction = transaction
        self.children = []
        self.start_time = 0.0
        self.end_time = 0.0
        self.duration = 0.0
        self.exclusive = 0.0
        self.activated = False

    def __enter__(self):
        if not self.transaction:
            return self
        pamagent_core.push_current(self.transaction, id(self), time.time())
        self.activated = True
        return self

    def __exit__(self, exc, value, tb):
        if not self.transaction:
            return
        if not self.activated:
            _logger.error('Runtime error. The __exit__() method was called prior to __enter__()')
            return
        transaction = self.transaction
        self.transaction = None
        self.end_time = time.time()
        pamagent_core.pop_current(transaction, id(self), self.end_time)


class FunctionTrace(TimeTrace):
    def __init__(self, transaction: int, func_name: str, name: str = None):
        super(FunctionTrace, self).__init__(transaction)
        self.name = name or func_name
        self.func_name = func_name

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, dict(name=self.name, func_name=self.func_name))

    def __enter__(self):
        if not self.transaction:
            return self
        pamagent_core.push_current(self.transaction, id(self), time.time(), func_name=self.func_name)
        self.activated = True
        return self


class ExternalTrace(TimeTrace):
    def __init__(self, transaction: int, library: str, url: str, method: Optional[str]=None):
        super(ExternalTrace, self).__init__(transaction)
        self.library = library
        self.url = url
        self.method = method
        self.params = {}

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, dict(
            library=self.library, url=self.url, method=self.method))

    def __enter__(self):
        if not self.transaction:
            return self
        pamagent_core.push_current_external(self.transaction, id(self), time.time(), self.url, self.library,
                                            self.method)
        self.activated = True
        return self


def ExternalTraceWrapper(wrapped, library, url, method):
    def dynamic_wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        if callable(url):
            if instance is not None:
                _url = url(instance, *args, **kwargs)
            else:
                _url = url(*args, **kwargs)

        else:
            _url = url

        if callable(method):
            if instance is not None:
                _method = method(instance, *args, **kwargs)
            else:
                _method = method(*args, **kwargs)

        else:
            _method = method

        with ExternalTrace(transaction, library, _url, _method):
            return wrapped(*args, **kwargs)

    return FuncWrapper(wrapped, dynamic_wrapper)


def external_trace(library, url, method=None):
    return functools.partial(ExternalTraceWrapper, library=library, url=url, method=method)


def wrap_external_trace(module, object_path, library, url, method=None):
    wrap_object(module, object_path, ExternalTraceWrapper, library, url, method)
