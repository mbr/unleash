import os
import subprocess

from unleash.util import VirtualEnv
from .utils_tree import in_tmpexport


PLUGIN_NAME = 'setupdist'
PLUGIN_DEPENDS = ['versions']


def _setup_py(ve, tmpdir, *args):
    a = [ve.python, os.path.join(tmpdir, 'setup.py')]
    a.extend(args)
    return ve.check_output(a)


def lint_release(ctx):
    info = ctx['info']
    log = ctx['log']
    issues = ctx['issues']

    log.info('Verifying release can generate source distribution.')
    try:
        with VirtualEnv.temporary() as ve, in_tmpexport(ctx['commit']) as td:
            log.debug('Running setup.py sdist')
            _setup_py(ve, td, 'sdist')

            # expected name is packagename-version.tar.gz
            pkgfn = '{}-{}.tar.gz'.format(info['pkg_name'],
                                          info['release_version'])
            fn = os.path.join(td, 'dist', pkgfn)
            if not os.path.exists(fn):
                issues.error('No source package {} found after setup.py sdist.'
                             .format(pkgfn),
                             'After calling \'setup.py sdist\', no source '
                             'distribution was generated (unleash expected a '
                             'file named {} in the subdirectory dist.'
                             .format(pkgfn))
    except subprocess.CalledProcessError as e:
        issues.error('setup.py sdist failed:\n{}'.format(e.output))
