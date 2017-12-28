import functools
import inspect
import logging
import sys

from wrapt import BoundFunctionWrapper, FunctionWrapper, ObjectProxy


_logger = logging.getLogger(__name__)


class _WrapperBase(ObjectProxy):
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


def wrap_function_wrapper(module, name, wrapper):
    return wrap_object(module, name, FunctionWrapper, (wrapper,))


def _module_name(obj):
    module_name = None
    if hasattr(obj, '__objclass__'):
        module_name = getattr(obj.__objclass__, '__module__', None)

    if module_name is None:
        module_name = getattr(obj, '__module__', None)

    if module_name is None:
        self = getattr(obj, '__self__', None)
        if self is not None and hasattr(self, '__class__'):
            module_name = getattr(self.__class__, '__module__', None)
    if module_name is None and hasattr(obj, '__class__'):
        module_name = getattr(obj.__class__, '__module__', None)

    if module_name and module_name not in sys.modules:
        module_name = '<%s>' % module_name

    # Fallback to unknown.
    if not module_name:
        module_name = '<unknown>'

    return module_name


def _object_context(obj):
    path = getattr(obj, '__qualname__', None)
    if path is None and hasattr(obj, '__class__'):
        path = getattr(obj.__class__, '__qualname__')
    mname = _module_name(obj)
    return mname, path


def object_context(target):
    """
    Returns a tuple identifying the supplied object. This will be of the form (module, object_path).
    """
    if isinstance(target, functools.partial):
        target = target.func

    details = getattr(target, '_pam_object_path', None)
    if details:
        return details
    parent = getattr(target, '_pam_parent', None)
    if parent:
        details = getattr(parent, '_pam_object_path', None)
    if details:
        return details
    source = getattr(target, '_pam_last_object', None)
    if source:
        details = getattr(target, '_pam_object_path', None)
        if details:
            return details
    else:
        source = target
    details = _object_context(source)
    try:
        if target is not source:
            if parent:
                parent._pam_object_path = details
            target._pam_object_path = details
        source._pam_object_path = details
    except Exception as exc:
        logging.debug("Error process object context. %s" % str(exc))
    return details


def callable_name(obj, separator=':'):
    """
    Returns a string name identifying the supplied object. This will be of the form 'module:object_path'.
    If object were a function, then the name would be 'module:function. If a class, 'module:class'.
    If a member function, 'module:class.function'.
    """
    return separator.join(object_context(obj))


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
