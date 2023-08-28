import ostar._ffi

from . import _ffi_api
from .base import Node


class AffineType(Node):
    def __eq__(self, other):
        return bool(ostar.ir.structural_equal(self, other))

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        from ostar.relay import pretty_print  # pylint: disable=import-outside-toplevel

        return pretty_print(self)


@ostar._ffi.register_object("TensorAffineType")
class TensorAffineType(AffineType):
    def __init__(self, scale, zero_point, dtype, axis=-1):
        self.__init_handle_by_constructor__(
            _ffi_api.TensorAffineType, scale, zero_point, dtype, axis
        )


@ostar._ffi.register_object("TupleAffineType")
class TupleAffineType(AffineType):
    def __init__(self, types):
        self.__init_handle_by_constructor__(_ffi_api.TupleAffineType, types)
