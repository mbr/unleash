import networkx as nx
from networkx.algorithms.dag import (is_directed_acyclic_graph, ancestors,
                                     descendants, topological_sort)


class DependencyGraph(object):
    def __init__(self):
        self.g = nx.DiGraph()

    def add_dependency(self, obj, depending_on):
        ng = self.g.copy()
        ng.add_edge(obj, depending_on)

        # check if adding these dependencies would add a cyclic dependency
        if not is_directed_acyclic_graph(ng):
            raise ValueError('Adding a dependency of {} on {} introduces a '
                             'dependency cycle!.'.format(obj, depending_on))

        self.g = ng

    def add_obj(self, obj, depends_on=[]):
        self.g.add_node(obj)

        ng = self.g.copy()
        ng.add_edges_from((obj, d) for d in depends_on)

        # check if adding these dependencies would add a cyclic dependency
        if not is_directed_acyclic_graph(ng):
            raise ValueError('Adding {} with dependencies {} introduces a '
                             'dependency cycle!.'.format(obj, depends_on))

        self.g = ng

    def get_dependants(self, obj):
        return self.g.predecessors(obj)

    def get_dependencies(self, obj):
        return self.g.successors(obj)

    def get_full_dependants(self, obj):
        return ancestors(self.g, obj)

    def get_full_dependencies(self, obj):
        return descendants(self.g, obj)

    def remove_obj(self, obj):
        self.g.remove_node(obj)

    def remove_dependency(self, obj, depending_on):
        self.g.remove_edge(obj, depending_on)

    def resolve_order(self):
        return topological_sort(self.g, reverse=True)
