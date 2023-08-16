import os
import logging
import json
import re

import ostar
from ostar.driver import ostarc
from ostar.driver.ostarc import OSTARCException
from ostar.driver.ostarc.composite_target import get_codegen_by_target, get_codegen_names
from ostar.ir.attrs import make_node, _ffi_api as attrs_api
from ostar.ir.transform import PassContext
from ostar.target import Target, TargetKind

# pylint: disable=invalid-name
logger = logging.getLogger("OSTARC")

# We can't tell the type inside an Array but all current options are strings so
# it can default to that. Bool is used alongside Integer but aren't distinguished
# between as both are represented by IntImm
INTERNAL_TO_NATIVE_TYPE = {"runtime.String": str, "IntImm": int, "Array": str}
INTERNAL_TO_HELP = {"runtime.String": " string", "IntImm": "", "Array": " options"}


def _valid_target_kinds():
    codegen_names = ostarc.composite_target.get_codegen_names()
    return filter(lambda target: target not in codegen_names, Target.list_kinds())


def _generate_target_kind_args(parser, kind_name):
    target_group = parser.add_argument_group(f"target {kind_name}")
    for target_option, target_type in TargetKind.options_from_name(kind_name).items():
        if target_type in INTERNAL_TO_NATIVE_TYPE:
            target_group.add_argument(
                f"--target-{kind_name}-{target_option}",
                type=INTERNAL_TO_NATIVE_TYPE[target_type],
                help=f"target {kind_name} {target_option}{INTERNAL_TO_HELP[target_type]}",
            )


def _generate_codegen_args(parser, codegen_name):
    codegen = get_codegen_by_target(codegen_name)
    pass_configs = PassContext.list_configs()

    if codegen["config_key"] is not None and codegen["config_key"] in pass_configs:
        target_group = parser.add_argument_group(f"target {codegen_name}")
        attrs = make_node(pass_configs[codegen["config_key"]]["type"])
        fields = attrs_api.AttrsListFieldInfo(attrs)
        for field in fields:
            for ostar_type, python_type in INTERNAL_TO_NATIVE_TYPE.items():
                if field.type_info.startswith(ostar_type):
                    target_option = field.name
                    target_group.add_argument(
                        f"--target-{codegen_name}-{target_option}",
                        type=python_type,
                        help=field.description,
                    )


def generate_target_args(parser):
    """Walks through the TargetKind registry and generates arguments for each Target's options"""
    parser.add_argument(
        "--target",
        help="compilation target as plain string, inline JSON or path to a JSON file",
        required=False,
    )
    for target_kind in _valid_target_kinds():
        _generate_target_kind_args(parser, target_kind)
    for codegen_name in get_codegen_names():
        _generate_codegen_args(parser, codegen_name)


def _reconstruct_target_kind_args(args, kind_name):
    kind_options = {}
    for target_option, target_type in TargetKind.options_from_name(kind_name).items():
        if target_type in INTERNAL_TO_NATIVE_TYPE:
            var_name = f"target_{kind_name.replace('-', '_')}_{target_option.replace('-', '_')}"
            option_value = getattr(args, var_name)
            if option_value is not None:
                kind_options[target_option] = getattr(args, var_name)
    return kind_options


def _reconstruct_codegen_args(args, codegen_name):
    codegen = get_codegen_by_target(codegen_name)
    pass_configs = PassContext.list_configs()
    codegen_options = {}

    if codegen["config_key"] is not None and codegen["config_key"] in pass_configs:
        attrs = make_node(pass_configs[codegen["config_key"]]["type"])
        fields = attrs_api.AttrsListFieldInfo(attrs)
        for field in fields:
            for ostar_type in INTERNAL_TO_NATIVE_TYPE:
                if field.type_info.startswith(ostar_type):
                    target_option = field.name
                    var_name = (
                        f"target_{codegen_name.replace('-', '_')}_{target_option.replace('-', '_')}"
                    )
                    option_value = getattr(args, var_name)
                    if option_value is not None:
                        codegen_options[target_option] = option_value
    return codegen_options


def reconstruct_target_args(args):
    """Reconstructs the target options from the arguments"""
    reconstructed = {}
    for target_kind in _valid_target_kinds():
        kind_options = _reconstruct_target_kind_args(args, target_kind)
        if kind_options:
            reconstructed[target_kind] = kind_options

    for codegen_name in get_codegen_names():
        codegen_options = _reconstruct_codegen_args(args, codegen_name)
        if codegen_options:
            reconstructed[codegen_name] = codegen_options

    return reconstructed


def validate_targets(parse_targets, additional_target_options=None):
    """
    Apply a series of validations in the targets provided via CLI.
    """
    ostar_target_kinds = ostar.target.Target.list_kinds()
    targets = [t["name"] for t in parse_targets]

    if len(targets) > len(set(targets)):
        raise OSTARCException("Duplicate target definitions are not allowed")

    if targets[-1] not in ostar_target_kinds:
        ostar_target_names = ", ".join(ostar_target_kinds)
        raise OSTARCException(
            f"The last target needs to be a OSTAR target. Choices: {ostar_target_names}"
        )

    ostar_targets = [t for t in targets if t in _valid_target_kinds()]
    if len(ostar_targets) > 2:
        verbose_ostar_targets = ", ".join(ostar_targets)
        raise OSTARCException(
            "Only two of the following targets can be used at a time. "
            f"Found: {verbose_ostar_targets}."
        )

    if additional_target_options is not None:
        for target_name in additional_target_options:
            if not any([target for target in parse_targets if target["name"] == target_name]):
                first_option = list(additional_target_options[target_name].keys())[0]
                raise OSTARCException(
                    f"Passed --target-{target_name}-{first_option}"
                    f" but did not specify {target_name} target"
                )


def tokenize_target(target):
    target_pattern = (
        r"(\-{0,2}[\w\-]+\=?"
        r"(?:[\w\+\-\.]+(?:,[\w\+\-\.])*"
        r"|[\'][\w\+\-,\s\.]+[\']"
        r"|[\"][\w\+\-,\s\.]+[\"])*"
        r"|,)"
    )

    return re.findall(target_pattern, target)


def parse_target(target):
    codegen_names = ostarc.composite_target.get_codegen_names()
    codegens = []

    ostar_target_kinds = ostar.target.Target.list_kinds()
    parsed_tokens = tokenize_target(target)

    split_codegens = []
    current_codegen = []
    split_codegens.append(current_codegen)
    for token in parsed_tokens:
        # every time there is a comma separating
        # two codegen definitions, prepare for
        # a new codegen
        if token == ",":
            current_codegen = []
            split_codegens.append(current_codegen)
        else:
            # collect a new token for the current
            # codegen being parsed
            current_codegen.append(token)

    # at this point we have a list of lists,
    # each item on the first list is a codegen definition
    # in the comma-separated values
    for codegen_def in split_codegens:
        # the first is expected to be the name
        name = codegen_def[0]
        is_ostar_target = name in ostar_target_kinds and name not in codegen_names
        raw_target = " ".join(codegen_def)
        all_opts = codegen_def[1:] if len(codegen_def) > 1 else []
        opts = {}
        for opt in all_opts:
            try:
                # deal with -- prefixed flags
                if opt.startswith("--"):
                    opt_name = opt[2:]
                    opt_value = True
                else:
                    opt = opt[1:] if opt.startswith("-") else opt
                    opt_name, opt_value = opt.split("=", maxsplit=1)

                    # remove quotes from the value: quotes are only parsed if they match,
                    # so it is safe to assume that if the string starts with quote, it ends
                    # with quote.
                    opt_value = opt_value[1:-1] if opt_value[0] in ('"', "'") else opt_value
            except ValueError:
                raise ValueError(f"Error when parsing '{opt}'")

            opts[opt_name] = opt_value

        codegens.append(
            {"name": name, "opts": opts, "raw": raw_target, "is_ostar_target": is_ostar_target}
        )

    return codegens


def is_inline_json(target):
    try:
        json.loads(target)
        return True
    except json.decoder.JSONDecodeError:
        return False


def _combine_target_options(target, additional_target_options=None):
    if additional_target_options is None:
        return target
    if target["name"] in additional_target_options:
        target["opts"].update(additional_target_options[target["name"]])
    return target


def _recombobulate_target(target):
    name = target["name"]
    opts = " ".join([f"-{key}={value}" for key, value in target["opts"].items()])
    return f"{name} {opts}"


def target_from_cli(target, additional_target_options=None):
    extra_targets = []

    if os.path.isfile(target):
        with open(target) as target_file:
            logger.debug("target input is a path: %s", target)
            target = "".join(target_file.readlines())
    elif is_inline_json(target):
        logger.debug("target input is inline JSON: %s", target)
    else:
        logger.debug("target input is plain text: %s", target)
        try:
            parsed_targets = parse_target(target)
        except ValueError as error:
            raise OSTARCException(f"Error parsing target string '{target}'.\nThe error was: {error}")

        validate_targets(parsed_targets, additional_target_options)
        ostar_targets = [
            _combine_target_options(t, additional_target_options)
            for t in parsed_targets
            if t["is_ostar_target"]
        ]

        # Validated target strings have 1 or 2 ostar targets, otherwise
        # `validate_targets` above will fail.
        if len(ostar_targets) == 1:
            target = _recombobulate_target(ostar_targets[0])
            target_host = None
        else:
            assert len(ostar_targets) == 2
            target = _recombobulate_target(ostar_targets[0])
            target_host = _recombobulate_target(ostar_targets[1])

        extra_targets = [
            _combine_target_options(t, additional_target_options)
            for t in parsed_targets
            if not t["is_ostar_target"]
        ]

    return ostar.target.Target(target, host=target_host), extra_targets
