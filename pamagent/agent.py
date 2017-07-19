from pamagent import pamagent_core

from pamagent.hooks import requests_hook, django_hook
from pamagent.wrapper import wrap_object, function_wrapper


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


def _init_builtin():
        requests_hook.patch()
        django_hook.patch()


def init():
    _init_builtin()
