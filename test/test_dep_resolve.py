from ..msysaur import resolve_dependencies

import sys
import ast

def hashable(x):
    try:
        hash(x)
        return True
    except TypeError:
        return False

def freeze_json(json_object):
    # recursively freeze json
    if isinstance(json_object, dict):
        # return key value pairs by frozenset
        kv_pairs = []
        for k,v in json_object.items():
            kv_pairs.append((k, freeze_json(v)))
        return frozenset(kv_pairs)
    elif isinstance(json_object, list):
        return tuple([freeze_json(v) for v in json_object])
    elif hashable(json_object):
        return json_object
    else:
        raise TypeError("unhashable type which is not dict or list: %s" % type(json_object))

def test_cuda114_resolve():
    expected = """
        {'name': 'cuda11.4', 'msys_pacman_name': None, 'Depends': ['gcc10-libs', 'gcc10', 'opencl-nvidia', 'nvidia-utils', 'python'], 'MakeDepends': [], 'CheckDepends': [], 'OptionalDepends': []}
    {'name': 'python', 'msys_pacman_name': 'python'}
    {'name': 'gcc10-libs', 'msys_pacman_name': None, 'Depends': ['glibc>=2.27'], 'MakeDepends': ['binutils', 'doxygen', 'git', 'libmpc', 'python'], 'CheckDepends': ['dejagnu', 'inetutils'], 'OptionalDepends': []}
    {'name': 'gcc10', 'msys_pacman_name': None, 'Depends': ['gcc10-libs=10.5.0-2', 'binutils>=2.28', 'libmpc', 'zstd'], 'MakeDepends': ['binutils', 'doxygen', 'git', 'libmpc', 'python'], 'CheckDepends': ['dejagnu', 'inetutils'], 'OptionalDepends': []}
    {'name': 'binutils', 'msys_pacman_name': 'binutils'}
    {'name': 'git', 'msys_pacman_name': 'git'}
    {'name': 'python', 'msys_pacman_name': 'python'}
    {'name': 'inetutils', 'msys_pacman_name': 'inetutils'}
    {'name': 'zstd', 'msys_pacman_name': 'zstd'}
    {'name': 'doxygen', 'msys_pacman_name': 'doxygen'}
    {'name': 'python', 'msys_pacman_name': 'python'}
    {'name': 'inetutils', 'msys_pacman_name': 'inetutils'}
    """
    expected = [ast.literal_eval(line) for line in expected.split("\n") if line.strip() != '']
    expected = [freeze_json(x) for x in expected]
    expected = set(expected)
    actual = set()
    for item in resolve_dependencies("cuda11.4"):
        print(item, file=sys.stderr)
        actual.add(freeze_json(item))
    assert expected == actual
