#!/usr/bin/env python3

import argparse
import collections
import os
import re
import textwrap
import sys
import typing


RequirementsByPieceType = typing.List[typing.Tuple[str, typing.Tuple[str, typing.List[str]]]]


# Maps named OSTAR piece (see description above) to a list of names of Python packages. Please use
# alphabetical order for each package list, and do not add version constraints here!
REQUIREMENTS_BY_PIECE: RequirementsByPieceType = [
    # Base requirements needed to install ostar.
    (
        "core",
        (
            "Base requirements needed to install ostar",
            [
                "attrs",
                "cloudpickle",
                "decorator",
                "numpy",
                "psutil",
                "scipy",
                "tornado",
            ],
        ),
    ),
    # Provide support for Arm(R) Ethos(TM)-U NPU.
    # Relay frontends.
    (
        "importer-caffe",
        (
            "Requirements for the Caffe importer",
            [
                "numpy",
                "protobuf",
                "scikit-image",
                "six",
            ],
        ),
    ),
    (
        "importer-caffe2",
        (
            "Requirements for the Caffe2 importer",
            [
                "future",  # Hidden dependency of torch.
                "torch",
            ],
        ),
    ),
    ("importer-coreml", ("Requirements for the CoreML importer", ["coremltools"])),
    ("importer-darknet", ("Requirements for the DarkNet importer", ["opencv-python"])),
    (
        "importer-keras",
        ("Requirements for the Keras importer", ["tensorflow", "tensorflow-estimator"]),
    ),
    (
        "importer-onnx",
        (
            "Requirements for the ONNX importer",
            [
                "future",  # Hidden dependency of torch.
                "onnx",
                "onnxoptimizer",
                "onnxruntime",
                "torch",
                "torchvision",
            ],
        ),
    ),
    (
        "importer-paddle",
        ("Requirements for the PaddlePaddle importer", ["paddlepaddle"]),
    ),
    (
        "importer-pytorch",
        (
            "Requirements for the PyTorch importer",
            [
                "future",  # Hidden dependency of torch.
                "torch",
                "torchvision",
            ],
        ),
    ),
    (
        "importer-tensorflow",
        ("Requirements for the TensorFlow importer", ["tensorflow", "tensorflow-estimator"]),
    ),
    (
        "importer-tflite",
        ("Requirements for the TFLite importer", ["tensorflow", "tensorflow-estimator", "tflite"]),
    ),
    (
        "ostarc",
        (
            "Requirements for the ostarc command-line tool",
            [
                "ethos-u-vela",
                "future",  # Hidden dependency of torch.
                "onnx",
                "onnxoptimizer",
                "onnxruntime",
                "paddlepaddle",
                "tensorflow",
                "tflite",
                "torch",
                "torchvision",
                "xgboost",
            ],
        ),
    ),
    # XGBoost, useful for autotuning on some targets.
    (
        "xgboost",
        (
            "Requirements for XGBoost autotuning",
            [
                "future",  # Hidden dependency of torch.
                "torch",
                "xgboost",
            ],
        ),
    ),
    # Development requirements
    (
        "dev",
        (
            "Requirements to develop OSTAR -- lint, docs, testing, etc.",
            [
                "astroid",  # pylint requirement, listed so a hard constraint can be included.
                "autodocsumm",
                "black",
                "commonmark",
                "cpplint",
                "docutils",
                "image",
                "matplotlib",
                "pillow",
                "pylint",
                "sphinx",
                "sphinx_autodoc_annotation",
                "sphinx_gallery",
                "sphinx_rtd_theme",
                "types-psutil",
            ],
        ),
    ),
]

ConstraintsType = typing.List[typing.Tuple[str, typing.Union[None, str]]]

CONSTRAINTS = [
    ("astroid", None),
    ("attrs", None),
    ("autodocsumm", None),
    ("black", "==20.8b1"),
    ("cloudpickle", None),
    ("commonmark", ">=0.7.3"),  # From PR #213.
    ("coremltools", None),
    ("cpplint", None),
    ("decorator", None),
    (
        "docutils",
        "<0.17",
    ),  # Work around https://github.com/readthedocs/sphinx_rtd_theme/issues/1115
    ("ethos-u-vela", "==3.7.0"),
    ("future", None),
    ("h5py", "==2.10.0"),
    ("image", None),
    ("matplotlib", None),
    # Workaround, see https://github.com/apache/ostar/issues/13647
    ("numpy", "<=1.23"),
    ("onnx", None),
    ("onnxoptimizer", None),
    ("onnxruntime", None),
    ("opencv-python", None),
    ("paddlepaddle", None),
    ("pillow", None),
    ("progressbar", None),
    ("protobuf", None),
    ("psutil", None),
    ("pylint", None),
    ("scikit-image", None),
    ("scipy", None),
    ("six", None),
    ("sphinx", None),
    ("sphinx_autodoc_annotation", None),
    ("sphinx_gallery", None),
    ("sphinx_rtd_theme", None),
    ("tensorflow", None),
    ("tensorflow-estimator", None),
    ("tflite", None),
    ("torch", None),
    ("torchvision", None),
    ("tornado", None),
]

REQUIRED_PIECES: typing.List[str] = ["core", "dev"]

PIECE_REGEX: typing.Pattern = re.compile(r"^[a-z0-9][a-z0-9-]*", re.IGNORECASE)

CONSTRAINT_REGEX: typing.Pattern = re.compile(r"(?:\^|\<|(?:~=)|(?:<=)|(?:==)|(?:>=)|\>)[^<>=\^,]+")

SEMVER_REGEX: typing.Pattern = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


def validate_requirements_by_piece() -> typing.List[str]:
    problems = []

    unseen_required_pieces = set(REQUIRED_PIECES)
    seen_pieces = set()

    # Ensure that core is listed first and dev is listed last.
    saw_core = False
    saw_dev = False

    if not isinstance(REQUIREMENTS_BY_PIECE, (list, tuple)):
        problems.append(f"must be list or tuple, see {REQUIREMENTS_BY_PIECE!r}")
        return problems

    for piece, value in REQUIREMENTS_BY_PIECE:
        if not isinstance(piece, str):
            problems.append(f"piece {piece!r}: must be str")
            continue

        if piece in unseen_required_pieces:
            unseen_required_pieces.remove(piece)

        piece_lower = piece.lower()
        if piece_lower in seen_pieces:
            problems.append(f"piece {piece}: listed twice")

        seen_pieces.add(piece_lower)

        if not saw_core and piece != "core":
            problems.append(f'piece {piece}: must list after "core" (core must be first)')
        elif piece == "core":
            saw_core = True

        if saw_dev:
            problems.append(f'piece {piece}: must list before "dev" (dev must be last)')
        elif piece == "dev":
            saw_dev = True

        if not isinstance(value, (tuple, list)) or len(value) != 2:
            problems.append(
                f'piece {piece}: should be formatted like ("{piece}", ("<requirements.txt comment>", ["dep1", "dep2", ...])). got: {value!r}'
            )
            continue

        description, deps = value

        if not isinstance(description, str):
            problems.append(f"piece {piece}: description should be a string, got {description!r}")

        if not isinstance(deps, (list, tuple)) or any(not isinstance(d, str) for d in deps):
            problems.append(f"piece {piece}: deps should be a list of strings, got {deps!r}")
            continue

        if list(sorted(deps)) != list(deps):
            problems.append(
                f"piece {piece}: deps must be sorted. Correct order:\n  {list(sorted(deps))!r}"
            )

        piece_deps = set()
        for d in deps:
            if CONSTRAINT_REGEX.search(d):
                problems.append(
                    f"piece {piece}: dependency {d} should not specify a version. "
                    "Add it to CONSTRAINTS instead."
                )

            if d.lower() in piece_deps:
                problems.append(f"piece {piece}: dependency {d} listed twice")

            piece_deps.add(d.lower())

    extras_pieces = [
        k for (k, _) in REQUIREMENTS_BY_PIECE if k not in ("dev", "core") if isinstance(k, str)
    ]
    sorted_extras_pieces = list(sorted(extras_pieces))
    if sorted_extras_pieces != list(extras_pieces):
        problems.append(
            'pieces other than "core" and "dev" must appear in alphabetical order: '
            f"{sorted_extras_pieces}"
        )

    return problems


def parse_semver(
    package: str, constraint: str, problems: typing.List[str]
) -> typing.Tuple[typing.List[str], int, int]:

    m = SEMVER_REGEX.match(constraint[1:])
    if not m:
        problems.append(f"{package}: invalid semver constraint {constraint}")
        return [], 0, 0

    min_ver_parts = [
        m.group("major"),
        m.group("minor"),
        m.group("patch")
        + (f"-{m.group('prerelease')}" if m.group("prerelease") else "")
        + (f"+{m.group('buildmetadata')}" if m.group("buildmetadata") else ""),
    ]

    # Major/minor version handling is simple
    for i, p in enumerate(min_ver_parts[:2]):
        x = int(p.strip())
        if x:
            return min_ver_parts, i, x

    # For patch version, consult only the numeric patch
    if m.group("patch"):
        patch_int = int(m.group("patch"))
        if patch_int or min_ver_parts[2] != m.group("patch"):
            return min_ver_parts, 2, patch_int

    # All 0's
    return min_ver_parts, 0, 0


def validate_constraints() -> typing.List[str]:
    problems = []

    if not isinstance(CONSTRAINTS, (list, tuple)):
        problems.append(f"must be list or tuple, see: {CONSTRAINTS!r}")

    seen_packages = set()
    all_deps = set()
    for _, (_, deps) in REQUIREMENTS_BY_PIECE:
        for d in deps:
            all_deps.add(d.lower())

    for package, constraint in CONSTRAINTS:
        if package in seen_packages:
            problems.append(f"{package}: specified twice")
        seen_packages.add(package)

        if package.lower() not in all_deps:
            problems.append(f"{package}: not specified in REQUIREMENTS_BY_PIECE")

        if constraint is None:  # None is just a placeholder that allows for comments.
            continue

        if not CONSTRAINT_REGEX.match(constraint):
            problems.append(
                f'{package}: constraint "{constraint}" does not look like a valid constraint'
            )

        if constraint.startswith("^"):
            parse_semver(package, constraint, problems)

    all_constrained_packages = [p for (p, _) in CONSTRAINTS]
    sorted_constrained_packages = list(sorted(all_constrained_packages))
    if sorted_constrained_packages != all_constrained_packages:
        problems.append(
            "CONSTRAINTS entries should be in this sorted order: " f"{sorted_constrained_packages}"
        )

    return problems


class ValidationError(Exception):
    """Raised when a validation error occurs."""

    @staticmethod
    def format_problems(config: str, problems: typing.List[str]) -> str:
        formatted = []
        for p in problems:
            assert isinstance(p, str), f"problems element not a str: {p}"
            formatted.append(
                "\n".join(
                    textwrap.wrap(
                        f"{config}: {p}", width=80, initial_indent=" * ", subsequent_indent="   "
                    )
                )
            )

        return "\n".join(formatted)

    def __init__(self, config: str, problems: typing.List[str]):
        super(ValidationError, self).__init__(self.format_problems(config, problems))
        self.problems = problems


def validate_or_raise():
    problems = validate_requirements_by_piece()
    if problems:
        raise ValidationError("REQUIREMENTS_BY_PIECE", problems)

    problems = validate_constraints()
    if problems:
        raise ValidationError("CONSTRAINTS", problems)


def semver_to_requirements(dep: str, constraint: str, joined_deps: typing.List[str]):
    problems: typing.List[str] = []
    min_ver_parts, fixed_index, fixed_part = parse_semver(dep, constraint, problems)
    text_problems = "\n" + "\n".join(f" * {p}" for p in problems)
    assert (
        not problems
    ), f"should not happen: validated semver {constraint} parses with problems:{text_problems}"

    max_ver_parts = (
        min_ver_parts[:fixed_index]
        + [str(fixed_part + 1)]
        + ["0" for _ in min_ver_parts[fixed_index + 1 :]]
    )
    joined_deps.append(f'{dep}>={".".join(min_ver_parts)},<{".".join(max_ver_parts)}')


def join_requirements() -> typing.Dict[str, typing.Tuple[str, typing.List[str]]]:
    validate_or_raise()

    constraints_map = collections.OrderedDict([(p.lower(), c) for (p, c) in CONSTRAINTS])

    to_return = collections.OrderedDict()
    all_deps = set()
    for piece, (description, deps) in REQUIREMENTS_BY_PIECE:
        joined_deps = []
        for d in deps:
            constraint = constraints_map.get(d.lower())
            if constraint is None:
                joined_deps.append(d)
                continue

            if constraint[0] == "^":
                semver_to_requirements(d, constraint, joined_deps)
            else:
                joined_deps.append(f"{d}{constraint}")

        if piece != "dev":
            all_deps.update(joined_deps)

        to_return[piece] = (description, joined_deps)

    to_return["all-prod"] = (
        "Combined dependencies for all OSTAR pieces, excluding dev",
        list(sorted(all_deps)),
    )

    return to_return


def join_and_write_requirements(args: argparse.Namespace):
    try:
        joined_deps = join_requirements()
    except ValidationError as e:
        print(f"ERROR: invalid requirements configuration in {__file__}:", file=sys.stderr)
        print(str(e), file=sys.stderr)
        sys.exit(2)

    if args.lint:
        sys.exit(0)

    output_dir = os.path.join(os.path.dirname(__file__), "requirements")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    elif not os.path.isdir(output_dir):
        print(
            f"ERROR: output directory {output_dir} exists but is not a dir. Delete it",
            file=sys.stderr,
        )
        sys.exit(2)

    for piece, (description, deps) in joined_deps.items():
        with open(os.path.join(output_dir, f"{piece}.txt"), "w") as f:
            f.write(
                f"# AUTOGENERATED by python/gen_requirements.py{os.linesep}"
                f"#{os.linesep}"
                f"# {description}{os.linesep}"
            )
            for d in deps:
                f.write(f"{d}{os.linesep}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lint", action="store_true", help="Just lint dependencies, don't generate anything"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    join_and_write_requirements(args)


if __name__ == "__main__":
    main()
