from ..msysaur import resolve_dependencies

def test_cuda114_resolve():
    result = list(resolve_dependencies("cuda11.4"))