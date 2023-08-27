import logging
import os
import sys
import re
import importlib
from abc import ABC
from abc import abstractmethod
from typing import Optional, List, Dict
from pathlib import Path

import numpy as np

from ostar import relay
from ostar import parser
from ostar.driver.ostarc import OSTARCException, OSTARCImportError
from ostar.driver.ostarc.model import OSTARCModel


# pylint: disable=invalid-name
logger = logging.getLogger("OSTARC")


class Frontend(ABC):
    """Abstract class for command line driver frontend.

    Provide a unified way to import models (as files), and deal
    with any required preprocessing to create a OSTAR module from it."""

    @staticmethod
    @abstractmethod
    def name():
        """Frontend name"""

    @staticmethod
    @abstractmethod
    def suffixes():
        """File suffixes (extensions) used by this frontend"""

    @abstractmethod
    def load(self, path, shape_dict=None, **kwargs):
        """Load a model from a given path.

        Parameters
        ----------
        path: str
            Path to a file
        shape_dict: dict, optional
            Mapping from input names to their shapes.

        Returns
        -------
        mod : ostar.IRModule
            The produced relay module.
        params : dict
            The parameters (weights) for the relay module.

        """


def lazy_import(pkg_name, from_pkg_name=None, hide_stderr=False):
    """Lazy import a frontend package or subpackage"""
    try:
        return importlib.import_module(pkg_name, package=from_pkg_name)
    except ImportError as error:
        raise OSTARCImportError(pkg_name) from error
    finally:
        if hide_stderr:
            sys.stderr = stderr

class OnnxFrontend(Frontend):
    """ONNX frontend for OSTARC"""

    @staticmethod
    def name():
        return "onnx"

    @staticmethod
    def suffixes():
        return ["onnx"]

    def load(self, path, shape_dict=None, **kwargs):
        onnx = lazy_import("onnx")

        # pylint: disable=E1101
        model = onnx.load(path)

        return relay.frontend.from_onnx(model, shape=shape_dict, **kwargs)


class PyTorchFrontend(Frontend):
    """PyTorch frontend for OSTARC"""

    @staticmethod
    def name():
        return "pytorch"

    @staticmethod
    def suffixes():
        # Torch Script is a zip file, but can be named pth
        return ["pth", "zip"]

    def load(self, path, shape_dict=None, **kwargs):
        torch = lazy_import("torch")

        if shape_dict is None:
            raise OSTARCException("--input-shapes must be specified for %s" % self.name())

        traced_model = torch.jit.load(path)
        traced_model.eval()  # Switch to inference mode

        # Convert shape dictionary to list for Pytorch frontend compatibility
        input_shapes = list(shape_dict.items())

        logger.debug("parse Torch model and convert into Relay computation graph")
        return relay.frontend.from_pytorch(
            traced_model, input_shapes, keep_quantized_weight=True, **kwargs
        )

class RelayFrontend(Frontend):
    """Relay frontend for OSTARC"""

    @staticmethod
    def name():
        return "relay"

    @staticmethod
    def suffixes():
        return ["relay"]

    def load(self, path, shape_dict=None, **kwargs):
        with open(path, "r", encoding="utf-8") as relay_text:
            text = relay_text.read()
        if shape_dict is None:
            logger.warning(
                "Specify --input-shapes to ensure that model inputs "
                "will not be considered as constants."
            )

        def _validate_text(text):
            """Check the provided file contents.
            The relay.txt artifact contained in the MLF is missing the version header and
            the metadata which is required to use meta[relay.Constant]."""

            if re.compile(r".*\#\[version\.*").match(text) is None:
                raise OSTARCException(
                    "The relay model does not include the required version information."
                )
            if re.compile(r".*meta\[.+\].*", re.DOTALL).match(text):
                if "#[metadata]" not in text:
                    raise OSTARCException(
                        "The relay model does not include the required #[metadata] section. "
                        "Use ir_mod.astext(show_meta_data=True) to export compatible code."
                    )

        _validate_text(text)

        ir_mod = parser.fromtext(text)

        if shape_dict:
            input_names = shape_dict.keys()
        else:
            input_names = []

        def _gen_params(ir_mod, skip_names=None):
            """Populate the all the params in the mode with ones."""
            main_func = ir_mod["main"]
            shape_dict = {p.name_hint: p.checked_type.concrete_shape for p in main_func.params}
            type_dict = {p.name_hint: p.checked_type.dtype for p in main_func.params}
            params = {}
            for name, shape in shape_dict.items():
                if skip_names and name in skip_names:
                    continue

                if "int" in type_dict[name]:
                    data = np.random.randint(128, size=shape, dtype=type_dict[name])
                else:
                    data = np.random.uniform(-1, 1, size=shape).astype(type_dict[name])
                params[name] = data
            return params

        params = _gen_params(ir_mod, skip_names=input_names)

        return ir_mod, params


ALL_FRONTENDS = [
    OnnxFrontend,
    PyTorchFrontend,
    RelayFrontend,
]


def get_frontend_names():
    """Return the names of all supported frontends

    Returns
    -------
    list : list of str
        A list of frontend names as strings

    """
    return [frontend.name() for frontend in ALL_FRONTENDS]


def get_frontend_by_name(name: str):
    """
    This function will try to get a frontend instance, based
    on the name provided.

    Parameters
    ----------
    name : str
        the name of a given frontend

    Returns
    -------
    frontend : ostar.driver.ostarc.Frontend
        An instance of the frontend that matches with
        the file extension provided in `path`.

    """

    for frontend in ALL_FRONTENDS:
        if name == frontend.name():
            return frontend()

    raise OSTARCException(
        "unrecognized frontend '{0}'. Choose from: {1}".format(name, get_frontend_names())
    )


def guess_frontend(path: str):
    """
    This function will try to imply which framework is being used,
    based on the extension of the file provided in the path parameter.

    Parameters
    ----------
    path : str
        The path to the model file.

    Returns
    -------
    frontend : ostar.driver.ostarc.Frontend
        An instance of the frontend that matches with
        the file extension provided in `path`.

    """

    suffix = Path(path).suffix.lower()
    if suffix.startswith("."):
        suffix = suffix[1:]

    for frontend in ALL_FRONTENDS:
        if suffix in frontend.suffixes():
            return frontend()

    raise OSTARCException("failed to infer the model format. Please specify --model-format")


def load_model(
    path: str,
    model_format: Optional[str] = None,
    shape_dict: Optional[Dict[str, List[int]]] = None,
    **kwargs,
):
    """Load a model from a supported framework and convert it
    into an equivalent relay representation.

    Parameters
    ----------
    path : str
        The path to the model file.
    model_format : str, optional
        The underlying framework used to create the model.
        If not specified, this will be inferred from the file type.
    shape_dict : dict, optional
        Mapping from input names to their shapes.

    Returns
    -------
    ostarc_model : OSTARCModel
        The produced model package.

    """

    if model_format is not None:
        frontend = get_frontend_by_name(model_format)
    else:
        frontend = guess_frontend(path)

    mod, params = frontend.load(path, shape_dict, **kwargs)

    return OSTARCModel(mod, params)
