from click import Option

import subprocess

from unleash.util import VirtualEnv
from .utils_tree import in_tmpexport

PLUGIN_NAME = 'tox_tests'


def setup(cli):
    cli.commands['release'].params.append(Option(
        ['--tests/--no-tests', '-t/-T'], default=True,
        help='Run unittests (default: enabled).'
    ))


def collect_info(ctx):
    info = ctx['info']

    info['tox_tests'] = ctx['opts']['tests']

    if not ctx['commit'].path_exists('tox.ini'):
        ctx['issues'].warn(
            'No tox.ini found.',
            'There was no tox.ini found in the project root. No tests will be '
            'run on the release.')
        info['tox_tests'] = False


def lint_release(ctx):
    if not ctx['info']['tox_tests']:
        return

    ctx['log'].debug('Installing tox in a new virtualenv')
    try:
        with VirtualEnv.temporary() as ve, in_tmpexport(ctx['commit']):
            ve.pip_install('tox')
            ctx['log'].debug('Running tests using tox')
            ve.check_output(['tox'])
    except subprocess.CalledProcessError as e:
        ctx['issues'].error('tox testing failed:\n{}'.format(e.output))
