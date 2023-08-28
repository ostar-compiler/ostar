import ostar._ffi
import ostar.error
from ostar._ffi import get_global_func, register_object
from ostar.runtime import Object, _ffi_node_api

from . import _ffi_api, json_compact


class Node(Object):
    """Base class of all IR Nodes."""


@register_object("SourceMap")
class SourceMap(Object):
    def add(self, name, content):
        return get_global_func("SourceMapAdd")(self, name, content)


@register_object("SourceName")
class SourceName(Object):
    def __init__(self, name):
        self.__init_handle_by_constructor__(_ffi_api.SourceName, name)  # type: ignore # pylint: disable=no-member


@register_object("Span")
class Span(Object):
    def __init__(self, source_name, line, end_line, column, end_column):
        self.__init_handle_by_constructor__(
            _ffi_api.Span, source_name, line, end_line, column, end_column  # type: ignore # pylint: disable=no-member
        )


@register_object
class EnvFunc(Object):
    def __call__(self, *args):
        return _ffi_api.EnvFuncCall(self, *args)  # type: ignore # pylint: disable=no-member

    @property
    def func(self):
        return _ffi_api.EnvFuncGetPackedFunc(self)  # type: ignore # pylint: disable=no-member

    @staticmethod
    def get(name):
        return _ffi_api.EnvFuncGet(name)  # type: ignore # pylint: disable=no-member


def load_json(json_str) -> Object:
    try:
        return _ffi_node_api.LoadJSON(json_str)
    except ostar.error.OSTARError:
        json_str = json_compact.upgrade_json(json_str)
        return _ffi_node_api.LoadJSON(json_str)


def save_json(node) -> str:
    return _ffi_node_api.SaveJSON(node)


def structural_equal(lhs, rhs, map_free_vars=False):
    lhs = ostar.runtime.convert(lhs)
    rhs = ostar.runtime.convert(rhs)
    return bool(_ffi_node_api.StructuralEqual(lhs, rhs, False, map_free_vars))  # type: ignore # pylint: disable=no-member


def get_first_structural_mismatch(lhs, rhs, map_free_vars=False):
    lhs = ostar.runtime.convert(lhs)
    rhs = ostar.runtime.convert(rhs)
    mismatch = _ffi_node_api.GetFirstStructuralMismatch(lhs, rhs, map_free_vars)  # type: ignore # pylint: disable=no-member
    if mismatch is None:
        return None
    else:
        return mismatch.lhs_path, mismatch.rhs_path


def assert_structural_equal(lhs, rhs, map_free_vars=False):
    lhs = ostar.runtime.convert(lhs)
    rhs = ostar.runtime.convert(rhs)
    _ffi_node_api.StructuralEqual(lhs, rhs, True, map_free_vars)  # type: ignore # pylint: disable=no-member


def structural_hash(node, map_free_vars=False):
    return _ffi_node_api.StructuralHash(node, map_free_vars)  # type: ignore # pylint: disable=no-member


def deprecated(
    method_name: str,
    new_method_name: str,
):
    import functools  # pylint: disable=import-outside-toplevel
    import warnings  # pylint: disable=import-outside-toplevel

    def _deprecate(func):
        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            warnings.warn(
                f"{method_name} is deprecated, use {new_method_name} instead",
                DeprecationWarning,
                stacklevel=2,
            )
            return func(*args, **kwargs)

        return _wrapper

    return _deprecate
