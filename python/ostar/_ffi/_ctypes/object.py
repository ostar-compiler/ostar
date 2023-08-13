
# pylint: disable=invalid-name
"""Runtime Object api"""
import ctypes
from ..base import _LIB, check_call
from .types import ArgTypeCode, RETURN_SWITCH, C_TO_PY_ARG_SWITCH, _wrap_arg_func
from .ndarray import _register_ndarray, NDArrayBase


ObjectHandle = ctypes.c_void_p
__init_by_constructor__ = None

OBJECT_TYPE = {}


OBJECT_INDEX = {}

_CLASS_OBJECT = None


def _set_class_object(object_class):
    global _CLASS_OBJECT
    _CLASS_OBJECT = object_class


def _register_object(index, cls):
    """register object class"""
    if issubclass(cls, NDArrayBase):
        _register_ndarray(index, cls)
        return
    OBJECT_TYPE[index] = cls
    OBJECT_INDEX[cls] = index


def _get_object_type_index(cls):
    """get the type index of object class"""
    return OBJECT_INDEX.get(cls)


def _return_object(x):
    handle = x.v_handle
    if not isinstance(handle, ObjectHandle):
        handle = ObjectHandle(handle)
    tindex = ctypes.c_uint()
    check_call(_LIB.OSTARObjectGetTypeIndex(handle, ctypes.byref(tindex)))
    cls = OBJECT_TYPE.get(tindex.value, _CLASS_OBJECT)
    if issubclass(cls, PyNativeObject):
        obj = _CLASS_OBJECT.__new__(_CLASS_OBJECT)
        obj.handle = handle
        return cls.__from_ostar_object__(cls, obj)
    # Avoid calling __init__ of cls, instead directly call __new__
    # This allows child class to implement their own __init__
    obj = cls.__new__(cls)
    obj.handle = handle
    return obj


RETURN_SWITCH[ArgTypeCode.OBJECT_HANDLE] = _return_object
C_TO_PY_ARG_SWITCH[ArgTypeCode.OBJECT_HANDLE] = _wrap_arg_func(
    _return_object, ArgTypeCode.OBJECT_HANDLE
)

C_TO_PY_ARG_SWITCH[ArgTypeCode.OBJECT_RVALUE_REF_ARG] = _wrap_arg_func(
    _return_object, ArgTypeCode.OBJECT_RVALUE_REF_ARG
)


class PyNativeObject:
    """Base class of all OSTAR objects that also subclass python's builtin types."""

    __slots__ = []

    def __init_ostar_object_by_constructor__(self, fconstructor, *args):
        """Initialize the internal ostar_object by calling constructor function.

        Parameters
        ----------
        fconstructor : Function
            Constructor function.

        args: list of objects
            The arguments to the constructor

        Note
        ----
        We have a special calling convention to call constructor functions.
        So the return object is directly set into the object
        """
        # pylint: disable=assigning-non-slot
        obj = _CLASS_OBJECT.__new__(_CLASS_OBJECT)
        obj.__init_handle_by_constructor__(fconstructor, *args)
        self.__ostar_object__ = obj


class ObjectBase(object):
    """Base object for all object types"""

    __slots__ = ["handle"]

    def __del__(self):
        if _LIB is not None:
            try:
                handle = self.handle
            except AttributeError:
                return

            check_call(_LIB.OSTARObjectFree(handle))

    def __init_handle_by_constructor__(self, fconstructor, *args):
        # assign handle first to avoid error raising
        # pylint: disable=not-callable
        self.handle = None
        handle = __init_by_constructor__(fconstructor, args)
        if not isinstance(handle, ObjectHandle):
            handle = ObjectHandle(handle)
        self.handle = handle

    def same_as(self, other):
        if not isinstance(other, ObjectBase):
            return False
        if self.handle is None:
            return other.handle is None
        return self.handle.value == other.handle.value
