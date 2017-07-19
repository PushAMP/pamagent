import wrapt

from pamagent.trace import wrap_external_trace


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


def patch():
    wrapt.register_post_import_hook(instrument_requests_api, 'requests.api')
    wrapt.register_post_import_hook(instrument_requests_sessions, 'request.sessions')
