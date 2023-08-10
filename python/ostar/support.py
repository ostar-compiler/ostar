
"""Support infra of OSTAR."""
import json
import textwrap
import ctypes
import os
import sys

import ostar
import ostar._ffi
from .runtime.module import Module
from . import get_global_func


def libinfo():
    get_lib_info_func = get_global_func("support.GetLibInfo", allow_missing=True)
    if get_lib_info_func is not None:
        lib_info = get_lib_info_func()
        if lib_info is None:
            return {}
    else:
        return {}
    return dict(lib_info.items())


def describe():
    """
    Print out information about OSTAR and the current Python environment
    """
    info = list((k, v) for k, v in libinfo().items())
    info = dict(sorted(info, key=lambda x: x[0]))
    print("Python Environment")
    sys_version = sys.version.replace("\n", " ")
    uname = os.uname()
    uname = f"{uname.sysname} {uname.release} {uname.version} {uname.machine}"
    lines = [
        f"OSTAR version    = {ostar.__version__}",
        f"Python version = {sys_version} ({sys.maxsize.bit_length() + 1} bit)",
        f"os.uname()     = {uname}",
    ]
    print(textwrap.indent("\n".join(lines), prefix="  "))
    print("CMake Options:")
    print(textwrap.indent(json.dumps(info, indent=2), prefix="  "))


class FrontendTestModule(Module):
    """A ostar.runtime.Module whose member functions are PackedFunc."""

    def __init__(self, entry_name=None):
        underlying_mod = get_global_func("testing.FrontendTestModule")()
        handle = underlying_mod.handle
        underlying_mod.handle = ctypes.c_void_p(0)

        super(FrontendTestModule, self).__init__(handle)
        if entry_name is not None:
            self.entry_name = entry_name

    def add_function(self, name, func):
        self.get_function("__add_function")(name, func)

    def __setitem__(self, key, value):
        self.add_function(key, value)


ostar._ffi._init_api("support", __name__)
