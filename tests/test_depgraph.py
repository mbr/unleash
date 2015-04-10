import pytest
from unleash.depgraph import DependencyGraph


@pytest.fixture
def dg():
    # our example dependency graph. it looks like this
    #
    # D -> B
    #       \
    #        A     E -> F
    #       /
    #      C

    g = DependencyGraph()
    g.add_obj('D', ['B'])
    g.add_obj('B', ['A'])
    g.add_obj('C', ['A'])
    g.add_obj('E', ['F'])

    return g


def test_get_full_dependencies(dg):
    assert dg.get_full_dependencies('D') == {'B', 'A'}


def test_get_full_dependants(dg):
    assert dg.get_full_dependants('A') == {'B', 'C', 'D'}
    assert dg.get_full_dependants('F') == {'E'}


def test_get_dependants(dg):
    assert set(dg.get_dependants('A')) == {'B', 'C'}


def test_get_dependencies(dg):
    assert dg.get_dependencies('B') == ['A']
    assert dg.get_dependencies('D') == ['B']
    assert dg.get_dependencies('E') == ['F']


def test_remove_obj(dg):
    dg.remove_obj('A')
    assert dg.get_dependencies('B') == []


def test_remove_dependency(dg):
    dg.remove_dependency('C', 'A')
    assert dg.get_full_dependants('A') == {'B', 'D'}


def test_resolve_order(dg):
    assert dg.resolve_order() == ['A', 'C', 'B', 'F', 'E', 'D']


def test_dag_enforced(dg):
    with pytest.raises(ValueError):
        dg.add_obj('A', ['B'])

    with pytest.raises(ValueError):
        dg.add_dependency('A', 'B')
