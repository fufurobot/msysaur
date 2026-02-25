from ..msysaur import resolve_dependencies

import sys

def test_cuda114_resolve():
    for item in resolve_dependencies("cuda11.4"):
        print(item, file=sys.stderr)