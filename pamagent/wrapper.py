import inspect
import sys

from wrapt import BoundFunctionWrapper, FunctionWrapper, ObjectProxy


class _WrapperBase(object):
    def __setattr__(self, name, value):
        if name.startswith('_pam_'):
            name = name.replace('_pam_', '_self_', 1)
            setattr(self, name, value)
        else:
            ObjectProxy.__setattr__(self, name, value)

    def __getattr__(self, name):
        if name.startswith('_pam_'):
            name = name.replace('_pam_', '_self_', 1)
            return getattr(self, name)
        else:
            return ObjectProxy.__getattr__(self, name)

    def __delattr__(self, name):
        if name.startswith('_pam_'):
            name = name.replace('_pam_', '_self_', 1)
            delattr(self, name)
        else:
            ObjectProxy.__delattr__(self, name)


class _PamBoundFunctionWrapper(_WrapperBase, BoundFunctionWrapper):
    pass


class FuncWrapper(_WrapperBase, FunctionWrapper):
    __bound_function_wrapper__ = _PamBoundFunctionWrapper


def resolve_path(target_module, name):
    if isinstance(target_module, str):
        __import__(target_module)
        target_module = sys.modules[target_module]
    parent = target_module
    path = name.split('.')
    attribute = path[0]
    original = getattr(parent, attribute)
    for attribute in path[1:]:
        parent = original
        if inspect.isclass(original):
            for _ in inspect.getmro(original):
                if attribute in vars(original):
                    original = vars(original)[attribute]
                    break
            else:
                original = getattr(original, attribute)
        else:
            original = getattr(original, attribute)
    return parent, attribute, original


def wrap_object(target_module, name, factory, *args, **kwargs):
    (parent, attribute, original) = resolve_path(target_module, name)
    wrapper = factory(original, *args, **kwargs)
    setattr(parent, attribute, wrapper)
    return wrapper
