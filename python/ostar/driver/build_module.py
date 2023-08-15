

# pylint: disable=invalid-name
"""The build utils in python."""
from typing import Union, Optional, List, Mapping

import warnings

import ostar.tir

from ostar import te

from ostar.runtime import Module
from ostar.runtime import ndarray
from ostar.ir import container
from ostar.tir import PrimFunc
from ostar.ir.module import IRModule
from ostar.te import tensor
from ostar.target import Target
from ostar.tir.buffer import Buffer
from ostar.tir.expr import Var
from ostar.driver import _ffi_api as _driver_ffi

from . import _ffi_api as ffi


def get_binds(args, compact=False, binds=None):
    binds, arg_list = ffi.get_binds(args, compact, binds)
    return binds, arg_list


def schedule_to_module(
    sch: te.Schedule,
    args: Optional[List[Union[Buffer, tensor.Tensor, Var]]] = None,
    name: str = "main",
    binds: Optional[Mapping[tensor.Tensor, Buffer]] = None,
) -> IRModule:
    return ffi.schedule_to_module(sch, args, name, binds)


def lower(
    inp: Union[te.Schedule, PrimFunc, IRModule],
    args: Optional[List[Union[Buffer, tensor.Tensor, Var]]] = None,
    name: str = "main",
    binds: Optional[Mapping[tensor.Tensor, Buffer]] = None,
    simple_mode: bool = False,
) -> IRModule:
    if isinstance(inp, IRModule):
        return ffi.lower_module(inp, simple_mode)
    if isinstance(inp, PrimFunc):
        return ffi.lower_primfunc(inp, name, simple_mode)
    if isinstance(inp, te.Schedule):
        return ffi.lower_schedule(inp, args, name, binds, simple_mode)
    raise ValueError(
        f"Expected input to be an IRModule, PrimFunc or te.Schedule, but got {type(inp)}"
    )


def build(
    inputs: Union[te.Schedule, PrimFunc, IRModule, Mapping[str, IRModule]],
    args: Optional[List[Union[Buffer, tensor.Tensor, Var]]] = None,
    target: Optional[Union[str, Target]] = None,
    target_host: Optional[Union[str, Target]] = None,
    runtime: Optional[
        "ostar.relay.backend.Runtime"
    ] = None,  # Type is annotated this way to avoid cyclic dependency
    name: Optional[str] = "default_function",
    binds: Optional[Mapping[tensor.Tensor, Buffer]] = None,
):
    if isinstance(inputs, te.Schedule):
        if args is None:
            raise ValueError("args must be given for build from schedule")
        input_mod = lower(inputs, args, name=name, binds=binds)
    elif isinstance(inputs, (list, tuple, container.Array)):
        merged_mod = ostar.IRModule({})
        for x in inputs:
            merged_mod.update(lower(x))
        input_mod = merged_mod
    elif isinstance(inputs, PrimFunc):
        input_mod = lower(inputs, name=name)
    elif isinstance(inputs, ostar.IRModule):
        input_mod = lower(inputs)
    elif not isinstance(inputs, (dict, container.Map)):
        raise ValueError(
            f"Inputs must be te.Schedule, IRModule, PrimFunc, "
            f"or dict of target to IRModule, "
            f"but got {type(inputs)}."
        )

    if not isinstance(inputs, (dict, container.Map)):
        target = Target.current() if target is None else target
        target = target if target else "llvm"
        target_input_mod = {target: input_mod}
    else:
        target_input_mod = inputs

    # Because modules can be created from a variety of sources, we annotate them
    # with the relevant attributes here to ensure they propagate
    annotated_mods = {}
    for tar, mod in target_input_mod.items():
        if not isinstance(tar, (str, Target)):
            raise ValueError("The key of inputs must be str or " "Target when inputs is dict.")
        if not isinstance(mod, ostar.IRModule):
            raise ValueError("inputs must be Schedule, IRModule," "or dict of str to IRModule.")
        annotated_mods[tar] = mod.with_attr("runtime", runtime)

    # TODO(mbs): Both CompilationConfig and TIRToRuntime implement the same host target
    #  defaulting logic, but there's currently no way to get back the decided host.
    if target_host is not None:
        warnings.warn(
            "target_host parameter is going to be deprecated. "
            "Please pass in ostar.target.Target(target, host=target_host) instead."
        )

    annotated_mods, target_host = Target.canon_target_map_and_host(annotated_mods, target_host)
    if not target_host:
        for tar, mod in annotated_mods.items():
            device_type = ndarray.device(tar.kind.name, 0).device_type
            if device_type == ndarray.cpu(0).device_type:
                target_host = tar
                break
    if not target_host:
        target_host = "llvm" if ostar.runtime.enabled("llvm") else "stackvm"

    annotated_mods, target_host = Target.canon_target_map_and_host(annotated_mods, target_host)

    rt_mod_host = _driver_ffi.tir_to_runtime(annotated_mods, target_host)

    annotated_mods, target_host = Target.canon_target_map_and_host(annotated_mods, target_host)

    if not isinstance(target_host, Target):
        target_host = Target(target_host)

    if str(runtime) == "crt" and runtime["system-lib"]:
        if target_host.kind.name == "c":
            create_csource_crt_metadata_module = ostar._ffi.get_global_func(
                "runtime.CreateCSourceCrtMetadataModule"
            )
            to_return = create_csource_crt_metadata_module([rt_mod_host], target_host, runtime)
        elif target_host.kind.name == "llvm":
            create_llvm_crt_metadata_module = ostar._ffi.get_global_func(
                "runtime.CreateLLVMCrtMetadataModule"
            )
            to_return = create_llvm_crt_metadata_module([rt_mod_host], target_host, runtime)
    else:
        to_return = rt_mod_host

    return OperatorModule.from_module(to_return, ir_module_by_target=annotated_mods, name=name)


class OperatorModule(Module):
    @classmethod
    def from_module(cls, mod, **kwargs):
        handle = mod.handle
        mod.handle = None
        return cls(handle, **kwargs)

    def __init__(self, handle, ir_module_by_target=None, name=None):
        super(OperatorModule, self).__init__(handle)
        self.ir_module_by_target = ir_module_by_target
        self.name = name
