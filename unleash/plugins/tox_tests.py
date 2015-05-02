from click import Option

import subprocess

from unleash import info, opts, commit, issues, log
from unleash.util import VirtualEnv
from .utils_tree import in_tmpexport

PLUGIN_NAME = 'tox_tests'


def setup(cli):
    cli.commands['release'].params.append(Option(
        ['--tests/--no-tests', '-t/-T'], default=True,
        help='Run unittests (default: enabled).'
    ))


def lint_release():
    info['tox_tests'] = opts['tests']

    if not commit.path_exists('tox.ini'):
        issues.warn(
            'No tox.ini found.',
            'There was no tox.ini found in the project root. No tests will be '
            'run on the release.')
        info['tox_tests'] = False

    if not info['tox_tests']:
        return

    log.info('Running tox tests')
    try:
        log.debug('Installing tox in a new virtualenv')
        with VirtualEnv.temporary() as ve, in_tmpexport(commit):
            ve.pip_install('tox')
            log.debug('Running tests using tox')
            ve.check_output(ve.get_binary('tox'))
    except subprocess.CalledProcessError as e:
        issues.error('tox testing failed:\n{}'.format(e.output))
