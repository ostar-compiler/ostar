import ostar._ffi

from ostar.runtime import Object
import ostar.runtime._ffi_node_api
from . import _ffi_api


@ostar._ffi.register_object
class Attrs(Object):
    def list_field_info(self):
        return _ffi_api.AttrsListFieldInfo(self)

    def keys(self):
        return [field.name for field in self.list_field_info()]

    def get_int_tuple(self, key):
        return tuple(x.value for x in self.__getattr__(key))

    def get_int(self, key):
        return self.__getattr__(key)

    def get_str(self, key):
        return self.__getattr__(key)

    def __getitem__(self, item):
        return self.__getattr__(item)


@ostar._ffi.register_object
class DictAttrs(Attrs):
    def _dict(self):
        return _ffi_api.DictAttrsGetDict(self)

    def keys(self):
        return [k for k, _ in self.items()]

    def __getitem__(self, k):
        return self._dict().__getitem__(k)

    def __contains__(self, k):
        return self._dict().__contains__(k)

    def items(self):
        """Get items from the map."""
        return self._dict().items()

    def __len__(self):
        return self._dict().__len__()


def make_node(type_key, **kwargs):
    args = [type_key]
    for k, v in kwargs.items():
        args += [k, v]
    return ostar.runtime._ffi_node_api.MakeNode(*args)
