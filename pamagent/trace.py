import logging
import time

from pamagent import pamagent_core


_logger = logging.getLogger(__name__)


class TimeTrace(object):
    node = None

    def __init__(self, transaction):
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
        pamagent_core.push_current(self.transaction.thread_id, id(self), time.time())
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
        parent_id = pamagent_core.pop_current(transaction.thread_id, id(self), self.end_time)


class FunctionTrace(TimeTrace):
    def __init__(self, transaction, name):
        super(FunctionTrace, self).__init__(transaction)
        self.name = name

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, dict(name=self.name))


class ExternalTrace(TimeTrace):
    def __init__(self, transaction, library, url, method=None):
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
        pamagent_core.push_current_external(self.transaction, id(self), time.time(), self.url, self.library)
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
        parent_id = pamagent_core.pop_current(transaction, id(self), self.end_time)