import wrapt

from pamagent.trace import wrap_external_trace


def instrument_requests_sessions(module):
    def url_method(obj, request, *args, **kwargs):
        return request.method.lower()

    def url_send(obj, request, *args, **kwargs):
        return request.url

    wrap_external_trace(module, 'Session.send', 'requests', url_send, url_method)


def instrument_requests_api(module):
    def url_request(method, url, *args, **kwargs):
        return url

    def url_method(method, url, *args, **kwargs):
        return method

    if hasattr(module, 'request'):
        wrap_external_trace(module, 'request', 'requests', url_request, url_method)


def patch():
    wrapt.register_post_import_hook(instrument_requests_api, 'requests.api')
    wrapt.register_post_import_hook(instrument_requests_sessions, 'request.sessions')
