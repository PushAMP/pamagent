import functools
import logging
import time
from collections import namedtuple
from urllib.parse import urlparse, urlunsplit

from pamagent import pamagent_core

from .transaction_cache import current_transaction
from .wrapper import FuncWrapper, wrap_object
from .trace import node_start_time, node_end_time, TraceNode

_logger = logging.getLogger(__name__)

TimeMetric = namedtuple('TimeMetric',
                        ['name', 'scope', 'duration', 'exclusive'])


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
        parent_id = pamagent_core.pop_current(transaction, id(self), self.end_time)


    def create_node(self):
        if self.node:
            return self.node(**dict((k, self.__dict__[k])
                                    for k in self.node._fields))
        return self

    def process_child(self, node):
        self.children.append(node)
        self.exclusive -= node.duration


_ExternalNode = namedtuple('_ExternalNode',
                           ['library', 'url', 'method', 'children', 'start_time', 'end_time', 'duration', 'exclusive',
                            'params'])


class ExternalNode(_ExternalNode):
    @property
    def details(self):
        if hasattr(self, '_details'):
            return self._details

        try:
            self._details = urlparse(self.url or '')
        except Exception:
            self._details = urlparse('http://unknown.url')

        return self._details

    def time_metrics(self, stats, root, parent):
        hostname = self.details.hostname or 'unknown'

        try:
            scheme = self.details.scheme.lower()
            port = self.details.port
        except Exception:
            scheme = None
            port = None

        if (scheme, port) in (('http', 80), ('https', 443)):
            port = None

        netloc = port and ('%s:%s' % (hostname, port)) or hostname
        name = 'External/%s/all' % netloc

        yield TimeMetric(name=name, scope='', duration=self.duration, exclusive=self.exclusive)

    def trace_node(self, stats, root, connections):

        hostname = self.details.hostname or 'unknown'

        try:
            scheme = self.details.scheme.lower()
            port = self.details.port
        except Exception:
            scheme = None
            port = None

        if (scheme, port) in (('http', 80), ('https', 443)):
            port = None

        netloc = port and ('%s:%s' % (hostname, port)) or hostname

        method = self.method or ''

        name = root.string_table.cache('External/%s/%s/%s' % (netloc, self.library, method))

        start_time = node_start_time(root, self)
        end_time = node_end_time(root, self)

        children = []

        root.trace_node_count += 1

        params = self.params

        details = self.details
        url = urlunsplit((details.scheme, details.netloc, details.path, '', ''))

        params['url'] = url

        return TraceNode(start_time=start_time, end_time=end_time, name=name, params=params, children=children,
                         label=None)


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

    def create_node(self):
        return ExternalNode(library=self.library, url=self.url, method=self.method, children=self.children,
                            start_time=self.start_time, end_time=self.end_time, duration=self.duration,
                            exclusive=self.exclusive, params=self.params)


def ExternalTraceWrapper(wrapped, library, url, method=None):
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

    def literal_wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()
        if transaction is None:
            return wrapped(*args, **kwargs)
        with ExternalTrace(transaction, library, url, method):
            return wrapped(*args, **kwargs)

    if callable(url) or callable(method):
        return FuncWrapper(wrapped, dynamic_wrapper)

    return FuncWrapper(wrapped, literal_wrapper)


def external_trace(library, url, method=None):
    return functools.partial(ExternalTraceWrapper, library=library, url=url, method=method)


def wrap_external_trace(module, object_path, library, url, method=None):
    wrap_object(module, object_path, ExternalTraceWrapper, library, url, method)


def instrument_requests_sessions(module):
    def url_request(obj, method, url, *args, **kwargs):
        return url

    def url_send(obj, request, *args, **kwargs):
        return request.url

    wrap_external_trace(module, 'Session.send', 'requests', url_send)


def instrument_requests_api(module):
    def url_request(method, url, *args, **kwargs):
        return url

    if hasattr(module, 'request'):
        wrap_external_trace(module, 'request', 'requests', url_request)
