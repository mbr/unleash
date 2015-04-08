import os

from pluginbase import PluginBase

from . import plugins

plugin_base = PluginBase(package='unleash.plugins')


def collect_plugins():
    # discover and load plugins
    plugin_source = plugin_base.make_plugin_source(
        persist=True,
        searchpath=[os.path.dirname(plugins.__file__)]
    )

    mods = []

    with plugin_source:
        for plugin_name in plugin_source.list_plugins():
            pl = plugin_source.load_plugin(plugin_name)

            # skip modules without ``PLUGIN_NAME`` attribute
            if not hasattr(pl, 'PLUGIN_NAME'):
                continue

            mods.append(pl)
    return mods


def notify_plugins(plugins, funcname, *args, **kwargs):
    rvs = []

    for plugin in plugins:
        func = getattr(plugin, funcname, None)

        if func is None or not callable(func):
            continue

        rvs.append(func(*args, **kwargs))

    return rvs
