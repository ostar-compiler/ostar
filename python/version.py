import os
import re
import argparse
import logging
import subprocess
import git

__version__ = "0.13.dev0"


PROJ_ROOT = os.path.dirname(os.path.abspath(os.path.expanduser(__file__)))


def py_str(cstr):
    return cstr.decode("utf-8")


def git_version():
    cmd = [
        "git",
        "describe",
        "--tags",
        "--match",
        "v[0-9]*.[0-9]*.[0-9]*",
        "--match",
        "v[0-9]*.[0-9]*.dev[0-9]*",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=PROJ_ROOT)
    (out, _) = proc.communicate()

    if proc.returncode != 0:
        msg = py_str(out)
        if msg.find("not a git repository") != -1:
            return __version__, __version__
        logging.warning("git describe: %s, use %s", msg, __version__)
        return __version__, __version__
    describe = py_str(out).strip()
    arr_info = describe.split("-")

    if arr_info[0].startswith("v"):
        arr_info[0] = arr_info[0][1:]

    if len(arr_info) == 1:
        return arr_info[0], arr_info[0]

    if len(arr_info) != 3:
        logging.warning("Invalid output from git describe %s", describe)
        return __version__, __version__

    dev_pos = arr_info[0].find(".dev")


    if dev_pos != -1:
        dev_version = arr_info[0][: arr_info[0].find(".dev")]
    else:
        dev_version = arr_info[0]

    pub_ver = "%s.dev%s" % (dev_version, arr_info[1])
    local_ver = "%s+%s" % (pub_ver, arr_info[2])
    return pub_ver, local_ver


def git_version(repo_path="."):
    try:
        repo = git.Repo(repo_path)
        describe = repo.git.describe("--tags", match="v[0-9]*.[0-9]*.[0-9]*", match="v[0-9]*.[0-9]*.dev[0-9]*")
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
    
def update(file_name, pattern, repl, dry_run=False):
    update = []
    hit_counter = 0
    need_update = False
    with open(file_name) as file:
        for l in file:
            result = re.findall(pattern, l)
            if result:
                assert len(result) == 1
                hit_counter += 1
                if result[0] != repl:
                    l = re.sub(pattern, repl, l)
                    need_update = True
                    print("%s: %s -> %s" % (file_name, result[0], repl))
                else:
                    print("%s: version is already %s" % (file_name, repl))

            update.append(l)
    if hit_counter != 1:
        raise RuntimeError("Cannot find version in %s" % file_name)

    if need_update and not dry_run:
        with open(file_name, "w") as output_file:
            for l in update:
                output_file.write(l)


def sync_version(pub_ver, local_ver, dry_run):
    update(
        os.path.join(PROJ_ROOT, "python", "ostar", "_ffi", "libinfo.py"),
        r"(?<=__version__ = \")[.0-9a-z\+]+",
        local_ver,
        dry_run,
    )

    update(
        os.path.join(PROJ_ROOT, "include", "ostar", "runtime", "c_runtime_api.h"),
        r'(?<=OSTAR_VERSION ")[.0-9a-z\+]+',
        pub_ver,
        dry_run,
    )
    update(
        os.path.join(PROJ_ROOT, "conda", "recipe", "meta.yaml"),
        r"(?<=version = ')[.0-9a-z\+]+",
        pub_ver,
        dry_run,
    )
    dev_pos = pub_ver.find(".dev")
    npm_ver = pub_ver if dev_pos == -1 else "%s.0-%s" % (pub_ver[:dev_pos], pub_ver[dev_pos + 1 :])
    update(
        os.path.join(PROJ_ROOT, "web", "package.json"),
        r'(?<="version": ")[.0-9a-z\-\+]+',
        npm_ver,
        dry_run,
    )


def main():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Detect and synchronize version.")
    parser.add_argument(
        "--print-version",
        action="store_true",
        help="Print version to the command line. No changes is applied to files.",
    )
    parser.add_argument(
        "--git-describe",
        action="store_true",
        help="Use git describe to generate development version.",
    )
    parser.add_argument("--dry-run", action="store_true")

    opt = parser.parse_args()
    pub_ver, local_ver = __version__, __version__
    if opt.git_describe:
        pub_ver, local_ver = git_version()
    if opt.print_version:
        print(local_ver)
    else:
        sync_version(pub_ver, local_ver, opt.dry_run)


if __name__ == "__main__":
    main()
