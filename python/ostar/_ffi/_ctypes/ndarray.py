
# pylint: disable=invalid-name
"""Runtime NDArray api"""
import ctypes
from ..base import _LIB, check_call, c_str
from ..runtime_ctypes import OSTARArrayHandle
from .types import RETURN_SWITCH, C_TO_PY_ARG_SWITCH, _wrap_arg_func, _return_handle


OSTARPyCapsuleDestructor = ctypes.CFUNCTYPE(None, ctypes.c_void_p)
_c_str_dltensor = c_str("dltensor")
_c_str_used_dltensor = c_str("used_dltensor")


# used for PyCapsule manipulation
if hasattr(ctypes, "pythonapi"):
    ctypes.pythonapi.PyCapsule_GetName.restype = ctypes.c_char_p
    ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.c_void_p
    ctypes.pythonapi.PyCapsule_New.restype = ctypes.py_object


def _from_dlpack(dltensor):
    dltensor = ctypes.py_object(dltensor)
    if ctypes.pythonapi.PyCapsule_IsValid(dltensor, _c_str_dltensor):
        ptr = ctypes.pythonapi.PyCapsule_GetPointer(dltensor, _c_str_dltensor)
        # enforce type to make sure it works for all ctypes
        ptr = ctypes.cast(ptr, ctypes.c_void_p)
        handle = OSTARArrayHandle()
        check_call(_LIB.OSTARArrayFromDLPack(ptr, ctypes.byref(handle)))
        ctypes.pythonapi.PyCapsule_SetName(dltensor, _c_str_used_dltensor)
        ctypes.pythonapi.PyCapsule_SetDestructor(dltensor, OSTARPyCapsuleDestructor(0))
        return _make_array(handle, False, False)
    raise ValueError("Expect a dltensor field, PyCapsule can only be consumed once")


def _dlpack_deleter(pycapsule):
    pycapsule = ctypes.cast(pycapsule, ctypes.py_object)
    if ctypes.pythonapi.PyCapsule_IsValid(pycapsule, _c_str_dltensor):
        ptr = ctypes.pythonapi.PyCapsule_GetPointer(pycapsule, _c_str_dltensor)
        # enforce type to make sure it works for all ctypes
        ptr = ctypes.cast(ptr, ctypes.c_void_p)
        _LIB.OSTARDLManagedTensorCallDeleter(ptr)
        ctypes.pythonapi.PyCapsule_SetDestructor(pycapsule, None)


_c_dlpack_deleter = OSTARPyCapsuleDestructor(_dlpack_deleter)


class NDArrayBase(object):
    """A simple Device/CPU Array object in runtime."""

    __slots__ = ["handle", "is_view"]
    # pylint: disable=no-member
    def __init__(self, handle, is_view=False):
        """Initialize the function with handle

        Parameters
        ----------
        handle : OSTARArrayHandle
            the handle to the underlying C++ OSTARArray
        """
        self.handle = handle
        self.is_view = is_view

    def __del__(self):
        if not self.is_view and _LIB:
            check_call(_LIB.OSTARArrayFree(self.handle))

    @property
    def _ostar_handle(self):
        return ctypes.cast(self.handle, ctypes.c_void_p).value

    def _copyto(self, target_nd):
        """Internal function that implements copy to target ndarray."""
        check_call(_LIB.OSTARArrayCopyFromTo(self.handle, target_nd.handle, None))
        return target_nd

    @property
    def shape(self):
        """Shape of this array"""
        return tuple(self.handle.contents.shape[i] for i in range(self.handle.contents.ndim))

    def to_dlpack(self):
        """Produce an array from a DLPack Tensor without copying memory

        Returns
        -------
        dlpack : DLPack tensor view of the array data
        """
        handle = ctypes.c_void_p()
        check_call(_LIB.OSTARArrayToDLPack(self.handle, ctypes.byref(handle)))
        return ctypes.pythonapi.PyCapsule_New(handle, _c_str_dltensor, _c_dlpack_deleter)


def _make_array(handle, is_view, is_container):
    global _OSTAR_ND_CLS
    handle = ctypes.cast(handle, OSTARArrayHandle)
    if is_container:
        tindex = ctypes.c_uint()
        check_call(_LIB.OSTARArrayGetTypeIndex(handle, ctypes.byref(tindex)))
        cls = _OSTAR_ND_CLS.get(tindex.value, _CLASS_NDARRAY)
    else:
        cls = _CLASS_NDARRAY

    ret = cls.__new__(cls)
    ret.handle = handle
    ret.is_view = is_view
    return ret


_OSTAR_COMPATS = ()


def _reg_extension(cls, fcreate):
    global _OSTAR_COMPATS
    _OSTAR_COMPATS += (cls,)
    if fcreate:
        fret = lambda x: fcreate(_return_handle(x))
        RETURN_SWITCH[cls._ostar_tcode] = fret
        C_TO_PY_ARG_SWITCH[cls._ostar_tcode] = _wrap_arg_func(fret, cls._ostar_tcode)


_OSTAR_ND_CLS = {}


def _register_ndarray(index, cls):
    global _OSTAR_ND_CLS
    _OSTAR_ND_CLS[index] = cls


_CLASS_NDARRAY = None


def _set_class_ndarray(cls):
    global _CLASS_NDARRAY
    _CLASS_NDARRAY = cls
