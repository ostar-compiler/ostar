import ostar._ffi

from .type import Type
from .expr import RelayExpr
from . import _ffi_api


@ostar._ffi.register_object("relay.Constructor")
class Constructor(RelayExpr):
    def __init__(self, name_hint, inputs, belong_to):
        self.__init_handle_by_constructor__(_ffi_api.Constructor, name_hint, inputs, belong_to)

    def __call__(self, *args):
        # pylint: disable=import-outside-toplevel
        from ostar import relay

        return relay.Call(self, args)


@ostar._ffi.register_object("relay.TypeData")
class TypeData(Type):
    def __init__(self, header, type_vars, constructors):
        self.__init_handle_by_constructor__(_ffi_api.TypeData, header, type_vars, constructors)
