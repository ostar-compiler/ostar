"""Common runtime ctypes."""
# pylint: disable=invalid-name
import ctypes
import json
import numpy as np
from .base import _LIB, check_call

ostar_shape_index_t = ctypes.c_int64


class ArgTypeCode(object):
    """Type code used in API calls"""

    INT = 0
    UINT = 1
    FLOAT = 2
    HANDLE = 3
    NULL = 4
    OSTAR_TYPE = 5
    DLDEVICE = 6
    DLTENSOR_HANDLE = 7
    OBJECT_HANDLE = 8
    MODULE_HANDLE = 9
    PACKED_FUNC_HANDLE = 10
    STR = 11
    BYTES = 12
    NDARRAY_HANDLE = 13
    OBJECT_RVALUE_REF_ARG = 14
    EXT_BEGIN = 15


class OSTARByteArray(ctypes.Structure):
    """Temp data structure for byte array."""

    _fields_ = [("data", ctypes.POINTER(ctypes.c_byte)), ("size", ctypes.c_size_t)]


class DataTypeCode(object):
    """DataType code in DLTensor."""

    INT = 0
    UINT = 1
    FLOAT = 2
    HANDLE = 3
    BFLOAT = 4


class DataType(ctypes.Structure):
    """OSTAR datatype structure"""

    _fields_ = [("type_code", ctypes.c_uint8), ("bits", ctypes.c_uint8), ("lanes", ctypes.c_uint16)]
    CODE2STR = {
        DataTypeCode.INT: "int",
        DataTypeCode.UINT: "uint",
        DataTypeCode.FLOAT: "float",
        DataTypeCode.HANDLE: "handle",
        DataTypeCode.BFLOAT: "bfloat",
    }
    NUMPY2STR = {
        np.dtype(np.bool_): "bool",
        np.dtype(np.int8): "int8",
        np.dtype(np.int16): "int16",
        np.dtype(np.int32): "int32",
        np.dtype(np.int64): "int64",
        np.dtype(np.uint8): "uint8",
        np.dtype(np.uint16): "uint16",
        np.dtype(np.uint32): "uint32",
        np.dtype(np.uint64): "uint64",
        np.dtype(np.float16): "float16",
        np.dtype(np.float32): "float32",
        np.dtype(np.float64): "float64",
        np.dtype(np.float_): "float64",
    }
    STR2DTYPE = {
        "bool": {"type_code": DataTypeCode.UINT, "bits": 1, "lanes": 1},
        "int8": {"type_code": DataTypeCode.INT, "bits": 8, "lanes": 1},
        "int16": {"type_code": DataTypeCode.INT, "bits": 16, "lanes": 1},
        "int32": {"type_code": DataTypeCode.INT, "bits": 32, "lanes": 1},
        "int64": {"type_code": DataTypeCode.INT, "bits": 64, "lanes": 1},
        "uint8": {"type_code": DataTypeCode.UINT, "bits": 8, "lanes": 1},
        "uint16": {"type_code": DataTypeCode.UINT, "bits": 16, "lanes": 1},
        "uint32": {"type_code": DataTypeCode.UINT, "bits": 32, "lanes": 1},
        "uint64": {"type_code": DataTypeCode.UINT, "bits": 64, "lanes": 1},
        "float16": {"type_code": DataTypeCode.FLOAT, "bits": 16, "lanes": 1},
        "float32": {"type_code": DataTypeCode.FLOAT, "bits": 32, "lanes": 1},
        "float64": {"type_code": DataTypeCode.FLOAT, "bits": 64, "lanes": 1},
    }

    def __init__(self, type_str):
        super(DataType, self).__init__()
        numpy_str_map = DataType.NUMPY2STR
        if type_str in numpy_str_map:
            type_str = numpy_str_map[type_str]
        elif isinstance(type_str, np.dtype):
            type_str = str(type_str)

        assert isinstance(type_str, str)

        str_dtype_map = DataType.STR2DTYPE
        if type_str in str_dtype_map:
            dtype_map = str_dtype_map[type_str]
            self.bits = dtype_map["bits"]
            self.type_code = dtype_map["type_code"]
            self.lanes = dtype_map["lanes"]
            return

        arr = type_str.split("x")
        head = arr[0]
        self.lanes = int(arr[1]) if len(arr) > 1 else 1
        bits = 32

        if head.startswith("int"):
            self.type_code = DataTypeCode.INT
            head = head[3:]
        elif head.startswith("uint"):
            self.type_code = DataTypeCode.UINT
            head = head[4:]
        elif head.startswith("float"):
            self.type_code = DataTypeCode.FLOAT
            head = head[5:]
        elif head.startswith("handle"):
            self.type_code = DataTypeCode.HANDLE
            bits = 64
            head = ""
        elif head.startswith("bfloat"):
            self.type_code = DataTypeCode.BFLOAT
            head = head[6:]
        elif head.startswith("custom"):
            # pylint: disable=import-outside-toplevel
            import ostar.runtime._ffi_api

            low, high = head.find("["), head.find("]")
            if not low or not high or low >= high:
                raise ValueError("Badly formatted custom type string %s" % type_str)
            type_name = head[low + 1 : high]
            self.type_code = ostar.runtime._ffi_api._datatype_get_type_code(type_name)
            head = head[high + 1 :]
        else:
            raise ValueError("Do not know how to handle type %s" % type_str)
        bits = int(head) if head else bits
        self.bits = bits

    def __repr__(self):
        # pylint: disable=import-outside-toplevel
        if self.bits == 1 and self.lanes == 1:
            return "bool"
        if self.type_code in DataType.CODE2STR:
            type_name = DataType.CODE2STR[self.type_code]
        else:
            import ostar.runtime._ffi_api

            type_name = "custom[%s]" % ostar.runtime._ffi_api._datatype_get_type_name(self.type_code)
        x = "%s%d" % (type_name, self.bits)
        if self.lanes != 1:
            x += "x%d" % self.lanes
        return x

    def __eq__(self, other):
        return (
            self.bits == other.bits
            and self.type_code == other.type_code
            and self.lanes == other.lanes
        )

    def __ne__(self, other):
        return not self.__eq__(other)


RPC_SESS_MASK = 128


class Device(ctypes.Structure):
    kDLCPU = 1
    kDLCUDA = 2
    kDLCUDAHost = 3

    _fields_ = [("device_type", ctypes.c_int), ("device_id", ctypes.c_int)]
    MASK2STR = {
        kDLCPU: "cpu",
        kDLCUDA: "cuda",
        kDLCUDAHost: "cuda_host",
        kDLCUDAManaged: "cuda_managed",
    }

    STR2MASK = {
        "llvm": kDLCPU,
        "stackvm": kDLCPU,
        "cpu": kDLCPU,
        "c": kDLCPU,
        "test": kDLCPU,
        "hybrid": kDLCPU,
        "composite": kDLCPU,
        "cuda": kDLCUDA,
    }

    def __init__(self, device_type, device_id):
        super(Device, self).__init__()
        self.device_type = int(device_type)
        self.device_id = device_id

    def _GetDeviceAttr(self, device_type, device_id, attr_id):
        # pylint: disable=import-outside-toplevel
        import ostar.runtime._ffi_api

        return ostar.runtime._ffi_api.GetDeviceAttr(device_type, device_id, attr_id)

    @property
    def exist(self):
        return self._GetDeviceAttr(self.device_type, self.device_id, 0) != 0

    @property
    def max_threads_per_block(self):
        return self._GetDeviceAttr(self.device_type, self.device_id, 1)

    @property
    def warp_size(self):
        return self._GetDeviceAttr(self.device_type, self.device_id, 2)

    @property
    def max_shared_memory_per_block(self):
        return self._GetDeviceAttr(self.device_type, self.device_id, 3)

    @property
    def compute_version(self):
        return self._GetDeviceAttr(self.device_type, self.device_id, 4)

    @property
    def device_name(self):
        return self._GetDeviceAttr(self.device_type, self.device_id, 5)

    @property
    def max_clock_rate(self):
        return self._GetDeviceAttr(self.device_type, self.device_id, 6)

    @property
    def multi_processor_count(self):
        return self._GetDeviceAttr(self.device_type, self.device_id, 7)

    @property
    def max_thread_dimensions(self):
        return json.loads(self._GetDeviceAttr(self.device_type, self.device_id, 8))

    @property
    def api_version(self):
        return self._GetDeviceAttr(self.device_type, self.device_id, 11)

    @property
    def driver_version(self):
        return self._GetDeviceAttr(self.device_type, self.device_id, 12)

    def texture_spatial_limit(self):
        return self._GetDeviceAttr(self.device_type, self.device_id, 12)

    def create_raw_stream(self):
        stream = ctypes.c_void_p()
        check_call(_LIB.OSTARStreamCreate(self.device_type, self.device_id, ctypes.byref(stream)))
        return stream

    def free_raw_stream(self, stream):
        check_call(_LIB.OSTARStreamFree(self.device_type, self.device_id, stream))

    def set_raw_stream(self, stream):
        check_call(_LIB.OSTARSetStream(self.device_type, self.device_id, stream))

    def sync(self, stream=None):
        """Synchronize until jobs finished at the context.

        Parameters
        ----------
        stream : OSTARStreamHandle
            Jobs in this stream should be finished.
        """
        check_call(_LIB.OSTARSynchronize(self.device_type, self.device_id, stream))

    def __eq__(self, other):
        return (
            isinstance(other, Device)
            and self.device_id == other.device_id
            and self.device_type == other.device_type
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(str(self))

    def __repr__(self):
        if self.device_type >= RPC_SESS_MASK:
            tbl_id = self.device_type / RPC_SESS_MASK - 1
            dev_type = self.device_type % RPC_SESS_MASK
            return "remote[%d]:%s(%d)" % (tbl_id, Device.MASK2STR[dev_type], self.device_id)
        return "%s(%d)" % (Device.MASK2STR[self.device_type], self.device_id)


class OSTARArray(ctypes.Structure):
    """OSTARValue in C API"""

    _fields_ = [
        ("data", ctypes.c_void_p),
        ("device", Device),
        ("ndim", ctypes.c_int),
        ("dtype", DataType),
        ("shape", ctypes.POINTER(ostar_shape_index_t)),
        ("strides", ctypes.POINTER(ostar_shape_index_t)),
        ("byte_offset", ctypes.c_uint64),
    ]


class ObjectRValueRef:
    __slots__ = ["obj"]

    def __init__(self, obj):
        self.obj = obj


OSTARArrayHandle = ctypes.POINTER(OSTARArray)
