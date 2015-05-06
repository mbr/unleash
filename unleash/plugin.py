import os

from pluginbase import PluginBase
from logbook import Logger

from . import plugins
from .depgraph import DependencyGraph
from .exc import InvocationError

plugin_base = PluginBase(package='unleash.plugins')
log = Logger('plugins')


class PluginGraph(DependencyGraph):
    NAME_ATTR = 'PLUGIN_NAME'
    DEP_ATTR = 'PLUGIN_DEPENDS'

    def __init__(self, *args, **kwargs):
        super(PluginGraph, self).__init__(*args, **kwargs)
        self.plugin_mods = {}

    def add_plugin(self, plugin):
        name = getattr(plugin, self.NAME_ATTR)
        self.plugin_mods[name] = plugin

        self.add_obj(name, depends_on=getattr(plugin, self.DEP_ATTR, []))

    def collect_plugins(self):
        # discover and load plugins
        plugin_source = plugin_base.make_plugin_source(
            persist=True,
            searchpath=[os.path.dirname(plugins.__file__)]
        )

        with plugin_source:
            for plugin_name in plugin_source.list_plugins():
                pl = plugin_source.load_plugin(plugin_name)

                # skip modules without ``PLUGIN_NAME`` attribute
                if not hasattr(pl, self.NAME_ATTR):
                    continue

                self.add_plugin(pl)

    def notify(self, funcname, *args, **kwargs):
        rvs = []
        order = self.resolve_order()

        log.debug('Sending {} signal to plugins in the following order: {}'
                  .format(funcname, order))

        for plugin_name in order:
            if not plugin_name in self.plugin_mods:
                raise InvocationError(
                    'Could not find plugin {}, which is required by {}'
                    .format(plugin_name, self.get_dependants(plugin_name)))

            plugin = self.plugin_mods[plugin_name]

            func = getattr(plugin, funcname, None)

            if func is None or not callable(func):
                continue

            rvs.append(func(*args, **kwargs))

        return rvs
