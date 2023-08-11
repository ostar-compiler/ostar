# pylint: disable=invalid-name, unused-import
import sys
import ctypes

from .base import _LIB, check_call, py_str, c_str, string_types, _FFI_MODE, _RUNTIME_ONLY

try:
    # pylint: disable=wrong-import-position,unused-import
    if _FFI_MODE == "ctypes":
        raise ImportError()
    from ._cy3.core import _register_object, _get_object_type_index
    from ._cy3.core import _reg_extension
    from ._cy3.core import convert_to_ostar_func, _get_global_func, PackedFuncBase
except (RuntimeError, ImportError) as error:
    # pylint: disable=wrong-import-position,unused-import
    if _FFI_MODE == "cython":
        raise error
    from ._ctypes.object import _register_object, _get_object_type_index
    from ._ctypes.ndarray import _reg_extension
    from ._ctypes.packed_func import convert_to_ostar_func, _get_global_func, PackedFuncBase


def register_object(type_key=None):
    object_name = type_key if isinstance(type_key, str) else type_key.__name__

    def register(cls):
        if hasattr(cls, "_type_index"):
            tindex = cls._type_index
        else:
            tidx = ctypes.c_uint()
            if not _RUNTIME_ONLY:
                check_call(_LIB.OSTARObjectTypeKey2Index(c_str(object_name), ctypes.byref(tidx)))
            else:
                # directly skip unknown objects during runtime.
                ret = _LIB.OSTARObjectTypeKey2Index(c_str(object_name), ctypes.byref(tidx))
                if ret != 0:
                    return cls
            tindex = tidx.value
        _register_object(tindex, cls)
        return cls

    if isinstance(type_key, str):
        return register

    return register(type_key)


def get_object_type_index(cls):
    return _get_object_type_index(cls)


def register_extension(cls, fcreate=None):
    assert hasattr(cls, "_ostar_tcode")
    if fcreate:
        raise ValueError("Extension with fcreate is no longer supported")
    _reg_extension(cls, fcreate)
    return cls


def register_func(func_name, f=None, override=False):
    if callable(func_name):
        f = func_name
        func_name = f.__name__

    if not isinstance(func_name, str):
        raise ValueError("expect string function name")

    ioverride = ctypes.c_int(override)

    def register(myf):
        """internal register function"""
        if not isinstance(myf, PackedFuncBase):
            myf = convert_to_ostar_func(myf)
        check_call(_LIB.OSTARFuncRegisterGlobal(c_str(func_name), myf.handle, ioverride))
        return myf

    if f:
        return register(f)
    return register


def get_global_func(name, allow_missing=False):
    return _get_global_func(name, allow_missing)


def list_global_func_names():
    plist = ctypes.POINTER(ctypes.c_char_p)()
    size = ctypes.c_uint()

    check_call(_LIB.OSTARFuncListGlobalNames(ctypes.byref(size), ctypes.byref(plist)))
    fnames = []
    for i in range(size.value):
        fnames.append(py_str(plist[i]))
    return fnames


def extract_ext_funcs(finit):
    fdict = {}

    def _list(name, func):
        fdict[name] = func

    myf = convert_to_ostar_func(_list)
    ret = finit(myf.handle)
    _ = myf
    if ret != 0:
        raise RuntimeError("cannot initialize with %s" % finit)
    return fdict


def remove_global_func(name):
    check_call(_LIB.OSTARFuncRemoveGlobal(c_str(name)))


def _get_api(f):
    flocal = f
    flocal.is_global = True
    return flocal


def _init_api(namespace, target_module_name=None):
    target_module_name = target_module_name if target_module_name else namespace
    if namespace.startswith("ostar."):
        _init_api_prefix(target_module_name, namespace[4:])
    else:
        _init_api_prefix(target_module_name, namespace)


def _init_api_prefix(module_name, prefix):
    module = sys.modules[module_name]

    for name in list_global_func_names():
        if not name.startswith(prefix):
            continue

        fname = name[len(prefix) + 1 :]
        target_module = module

        if fname.find(".") != -1:
            continue
        f = get_global_func(name)
        ff = _get_api(f)
        ff.__name__ = fname
        ff.__doc__ = "OSTAR PackedFunc %s. " % fname
        setattr(target_module, ff.__name__, ff)
