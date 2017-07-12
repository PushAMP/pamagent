import inspect
import functools
import logging

from pamagent import pamagent_core

from .web_transaction import WSGIApplicationWrapper
from .transaction_cache import current_transaction
from .trace import ExternalTrace
from .wrapper import FuncWrapper, wrap_object


_logger = logging.getLogger(__name__)


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


def function_wrapper(wrapper):
    def _wrapper(wrapped, instance, args, kwargs):
        target_wrapped = args[0]
        if instance is None:
            target_wrapper = wrapper
        elif inspect.isclass(instance):
            target_wrapper = wrapper.__get__(None, instance)
        else:
            target_wrapper = wrapper.__get__(instance, type(instance))
        return FuncWrapper(target_wrapped, target_wrapper)

    return FuncWrapper(wrapper, _wrapper)


def external_trace(library, url, method=None):
    return functools.partial(ExternalTraceWrapper, library=library, url=url, method=method)


def wrap_external_trace(module, object_path, library, url, method=None):
    wrap_object(module, object_path, ExternalTraceWrapper, library, url, method)


def post_function(function):
    @function_wrapper
    def _wrapper(wrapped, instance, args, kwargs):
        result = wrapped(*args, **kwargs)
        if instance is not None:
            function(instance, *args, **kwargs)
        else:
            function(*args, **kwargs)
        return result

    return _wrapper


def PostFunctionWrapper(wrapped, function):
    return post_function(function)(wrapped)


def wrap_post_function(module, object_path, function):
    return wrap_object(module, object_path, PostFunctionWrapper, (function,))


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


def instrument_django_core_handlers_wsgi(module):
    """
    Wrap the WSGI application entry point. If this is also wrapped from the WSGI script file or by the WSGI hosting
    mechanism then those will take precedence.
    """

    import django

    framework = ('Django', django.get_version())
    module.WSGIHandler.__call__ = WSGIApplicationWrapper(module.WSGIHandler.__call__, framework=framework)
