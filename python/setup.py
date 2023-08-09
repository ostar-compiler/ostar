import os
import shutil
import sys
import sysconfig
import pathlib
import platform
import git 

from setuptools import find_packages
from setuptools.dist import Distribution

if "--inplace" in sys.argv:
    from distutils.core import setup
    from distutils.extension import Extension
else:
    from setuptools import setup
    from setuptools.extension import Extension

CURRENT_DIR = os.path.dirname(__file__)
FFI_MODE = os.environ.get("OSTAR_FFI", "auto")
CONDA_BUILD = os.getenv("CONDA_BUILD") is not None


# todo: redit this function
def get_lib_path():
    import sys
    sys.path.append("./ostar/_ffi")
    import libinfo 
    version = libinfo.__version__
    lib_path = libinfo.find_lib_path()
    print(lib_path)
    
    libs = [lib_path[0]]
    if "runtime" not in libs[0]:
        for name in lib_path[1:]:
            if "runtime" in name:
                libs.append(name)
                break

    for name in lib_path:
        candidate_path = os.path.join(os.path.dirname(name), "standalone_crt")
        if os.path.isdir(candidate_path):
            libs.append(candidate_path)
            break

    for name in lib_path:
        candidate_path = os.path.join(os.path.dirname(name), "microostar_template_projects")
        if os.path.isdir(candidate_path):
            libs.append(candidate_path)
            break

    for name in lib_path:
        candidate_path = os.path.abspath(os.path.join(os.path.dirname(name), "..", "configs"))
        if os.path.isdir(candidate_path):
            libs.append(candidate_path)
            break

    return libs, version


def git_version(repo_path="."):
    try:
        repo = git.Repo(repo_path)
        describe = repo.git.describe("--tags", 
                                     match=[
                                         "v[0-9]*.[0-9]*.[0-9]*",
                                        "v[0-9]*.[0-9]*.dev[0-9]*"]
                                    )
        
        arr_info = describe.split("-")
        if arr_info[0].startswith("v"):
            arr_info[0] = arr_info[0][1:]
        if len(arr_info) == 1:
            return arr_info[0], arr_info[0]
        if len(arr_info) != 3:
            return __version__, __version__
        dev_pos = arr_info[0].find(".dev")
        if dev_pos != -1:
            dev_version = arr_info[0][:dev_pos]
        else:
            dev_version = arr_info[0]
        pub_ver = "%s.dev%s" % (dev_version, arr_info[1])
        local_ver = "%s+%s" % (pub_ver, arr_info[2])
        return pub_ver, local_ver
    except git.InvalidGitRepositoryError:
        return __version__, __version__
    
def git_describe_version(original_version):
    _, gd_version = git_version()
    if gd_version != original_version and "--inplace" not in sys.argv:
        print("Use git describe based version %s" % gd_version)
    return gd_version


LIB_LIST, __version__ = get_lib_path()
__version__ = git_describe_version(__version__)

class BinaryDistribution(Distribution):
    def has_ext_modules(self):
        return True

    def is_pure(self):
        return False


setup_kwargs = {}
if not CONDA_BUILD:
    with open("MANIFEST.in", "w") as fo:
        for path in LIB_LIST:
            if os.path.isfile(path):

                if os.path.dirname(path) != os.path.join(os.getcwd(), "ostar"):
                    shutil.copy(path, os.path.join(CURRENT_DIR, "ostar"))

                _, libname = os.path.split(path)
                fo.write(f"include ostar/{libname}\n")

            if os.path.isdir(path):
                _, libname = os.path.split(path)
                shutil.copytree(path, os.path.join(CURRENT_DIR, "ostar", libname), dirs_exist_ok=True)
                fo.write(f"recursive-include ostar/{libname} *\n")

    setup_kwargs = {"include_package_data": True}


def get_package_data_files():
    return ["relay/std/prelude.rly", "relay/std/core.rly"]


sys.path.insert(0, os.path.dirname(__file__))
import gen_requirements

sys.path.pop(0)

requirements = gen_requirements.join_requirements()
extras_require = {
    piece: deps for piece, (_, deps) in requirements.items() if piece not in ("all", "core")
}

setup(
    name="ostar",
    version=__version__,
    description="Tiny-OSTAR",
    url="https://github.com/ostar-compiler/ostar",
    download_url="https://github.com/ostar-compiler/ostar/tags",
    author="m0dulo",
    license="Apache",
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
    ],
    keywords="machine learning",
    zip_safe=False,
    entry_points={"console_scripts": ["ostarc = ostar.driver.ostarc.main:main"]},
    install_requires=requirements["core"][1],
    extras_require=extras_require,
    packages=find_packages(),
    package_dir={"ostar": "ostar"},
    package_data={"ostar": get_package_data_files()},
    distclass=BinaryDistribution,
    **setup_kwargs,
)


if not CONDA_BUILD:
    # Wheel cleanup
    os.remove("MANIFEST.in")
    for path in LIB_LIST:
        _, libname = os.path.split(path)
        path_to_be_removed = f"ostar/{libname}"

        if os.path.isfile(path_to_be_removed):
            os.remove(path_to_be_removed)

        if os.path.isdir(path_to_be_removed):
            shutil.rmtree(path_to_be_removed)
