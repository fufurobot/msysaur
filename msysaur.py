# an script to fetch repo from aur.archlinux.org and convert it to msys2 repo

# the key of converting is to add prefix mingw-w64-x86_64- for pacman package name

# this is tested under python of msys2 MINGW64 only

__doc__ = """
msysaur is a Python script that fetches repositories from aur.archlinux.org and converts them to msys2 repositories.

This script is designed to work with the MSYS2 environment on Windows, Linux, and macOS. It uses the MSYSTEM environment variable to determine the prefix for the conversion.

The script supports two main modes of operation: search and install. The search mode uses the RPC API to search for packages based on a given package name. The install mode fetches a repository from aur.archlinux.org, adds a prefix to the cloned repository, and prepares it for installation.

The script also checks for the availability of git and makepkg on the system's PATH.

Usage:
    msysaur.py [-h] [-S | -Ss] package ...

Options:
    -h, --help     Show this help message and exit.
    -S, --install  Install the specified package(s) from aur.archlinux.org.
    -Ss, --search  Search for the specified package(s) on aur.archlinux.org.

Example:
    msysaur.py -Ss cuda
    msysaur.py -S git-git olamma-cuda-git pikaur
"""

UNIQUE_PREFIXES = [
    'mingw-w64-clang-aarch64',
    'mingw-w64-clang-x86_64',
    'mingw-w64-ucrt-x86_64',
    'mingw-w64-x86_64',
]

PREFIX_DICT = {
    "MINGW64": "mingw-w64-x86_64",
    "UCRT64": "mingw-w64-ucrt-x86_64",
    "CLANG64": "mingw-w64-clang-x86_64",
    "CLANGARM64": "mingw-w64-clang-aarch64",
}

import argparse
import os
import subprocess
import sys
import urllib
import urllib.request
import urllib.parse
import json
import shutil

# we act just like an aur wrapper
# we read the env variable MSYSTEM to determine the prefix
# we only support msysaur -Ss to search aur and -S to install from aur for now

# for other commands, we just delegate to pacman


def get_prefix():
    prefix = os.getenv("MSYSTEM")
    if prefix:
        prefix = PREFIX_DICT.get(prefix)
    return prefix

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="+")
    args = parser.parse_args()
    # check first option is -S or -Ss
    if args.command[0] not in ["-S", "-Ss"]:
        subprocess.run(["pacman"] + args.command)
        return

    prefix = get_prefix()
    if not prefix:
        print("MSYSTEM is not set or not supported")
        sys.exit(1)
    
    # check git and makepkg on PATH
    if "git" not in subprocess.check_output(["which", "git"]).decode():
        print("git is not found in PATH")
        sys.exit(1)
    if "makepkg" not in subprocess.check_output(["which", "makepkg"]).decode():
        print("makepkg is not found in PATH")
        sys.exit(1)

def search_mode(package):
    # use rpc to search
    curl_cmd = f"""curl -X 'GET' \
  'https://aur.archlinux.org/rpc/v5/search/{package}' \
  -H 'accept: application/json'"""
    result = subprocess.check_output(curl_cmd, shell=True)
    # parse name and description from "results"
    result_json = json.loads(result)
    for result in result_json["results"]:
        name = result["Name"]
        description = result["Description"]
        print(f"{name} - {description}")

def resolve_dependencies(*packages):
    # first we use pacman with prefix to check whether packages are available in msys2/mingw repository
    packages = list(packages)
    prefix = get_prefix()
    for pkg in packages:
        # check original name and name with prefix
        prefixed_name = prefix + "-" + pkg
        for check_pkg in [pkg, prefixed_name]:
            return_code = subprocess.call(["pacman", "-Si", check_pkg])
            if return_code == 0:
                yield {
                    "name": pkg,
                    "msys_pacman_name": check_pkg,
                }
                packages.remove(pkg)
                break

    # use rpc to get dependencies and make dependencies list
    # use urllib to construct curl reqest
    #curl -X 'GET' \
    #'https://aur.archlinux.org/rpc/v5/info?arg%5B%5D=git-git&arg%5B%5D=ollama-cuda-git&arg%5B%5D=pikaur' \
    #-H 'accept: application/json'
    query_string = urllib.parse.urlencode({"arg[]": packages}, doseq=True)
    request = urllib.request.Request(f"https://aur.archlinux.org/rpc/v5/info?{query_string}", headers={"accept": "application/json"}, method="GET")
    response = urllib.request.urlopen(request)
    pkginfos = json.loads(response.read())["results"]

    collected_dependencies = []

    for pkginfo in pkginfos:
        deps = pkginfo.get("Depends", [])
        make_deps = pkginfo.get("MakeDepends", [])
        check_deps = pkginfo.get("CheckDepends", [])
        opt_deps = pkginfo.get("OptionalDepends", [])
        resolved_pkg = {"name": pkginfo["Name"], "msys_pacman_name": None, "Depends": deps, "MakeDepends": make_deps, "CheckDepends": check_deps, "OptionalDepends": opt_deps}
        # recursively parse dependencies
        yield resolved_pkg
        collected_dependencies.extend(deps)
        # FIXME: now we install everything including make_depends, check_depends do not clean up after install the package. we should clean up make_depends and check_depends after install
        collected_dependencies.extend(make_deps)
        collected_dependencies.extend(check_deps)
    # FIXME: tailed recursion can be optimized as loop
    yield from resolve_dependencies(*collected_dependencies)

def install_mode(package):
    # fetch repo from aur

    subprocess.run(["git", "clone", "https://aur.archlinux.org/" + package + ".git"])
    # add prefix to cloned repo
    prefix = get_prefix()
    new_name =  prefix + "-" + package
    shutil.move(package, new_name)
    subprocess.run(["cd", new_name])
    
    # TODO get dependencies from rpc
