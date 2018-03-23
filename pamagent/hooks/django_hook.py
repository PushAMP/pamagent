import wrapt

from ..web_transaction import wsgi_application_wrapper


def instrument_django_core_handlers_wsgi(module):
    """
    Wrap the WSGI application entry point. If this is also wrapped from the WSGI script file or by the WSGI hosting
    mechanism then those will take precedence.
    """

    import django

    framework = ('Django', django.get_version())
    module.WSGIHandler.__call__ = wsgi_application_wrapper(module.WSGIHandler.__call__, framework=framework)


def patch():
    wrapt.register_post_import_hook(instrument_django_core_handlers_wsgi, 'django.core.handlers.wsgi')
