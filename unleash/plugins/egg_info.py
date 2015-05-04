from pkginfo import Develop
from unleash import commit, log, info
from unleash.util import VirtualEnv

from .utils_tree import in_tmpexport


PLUGIN_NAME = 'egg_info'


def collect_info():
    log.info('Collecting egg-info')
    with VirtualEnv.temporary() as ve, in_tmpexport(commit):
        ve.check_output([ve.python, 'setup.py', 'egg_info'])
        info['egg_info'] = Develop('.')
