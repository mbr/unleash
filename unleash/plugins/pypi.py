import os
import subprocess
import sys

from click import Option
from six.moves import shlex_quote
from .utils_tree import in_tmpexport
from unleash import log, opts, info, issues, commit
from unleash.util import VirtualEnv


PLUGIN_NAME = 'pypi'
DEFAULT_GPG_HOMEDIR = os.path.expanduser('~/.gnupg/')


def setup(cli):
    cli.commands['publish'].params.append(Option(
        ['--sign/--no-sign', '-s/-S'], default=True,
        help='Turn code signing on or off.'
    ))
    cli.commands['publish'].params.append(Option(
        ['--identity', '-i'],
        help='Identity to use when signing.'
    ))


def collect_info():
    py = sys.executable
    if not py:
        issues.error('Could not determine Python executable',
                     'unleash could not (through sys.executable) determine the '
                     'path to your Python interpreter. This is required for '
                     'launching other programs.')

    info['python'] = py


def publish_release():
    with in_tmpexport(commit) as td, VirtualEnv.temporary() as ve:
        if opts['dry_run']:
            log.info('Creating source distribution, no upload (dry-run)')
            subprocess.check_output(
                [ve.python, 'setup.py', 'sdist'],
                cwd=td,
            )
        else:
            ve.pip_install(td)

            args = [ve.python, 'setup.py',
                    'sdist',
                    'upload'
                    ]

            if opts['sign']:
                args.append('-s')

                if opts['identity'] is not None:
                    args.extend(['-i', shlex_quote(opts['identity'])])
                    log.info('Uploading signed source distribution to PyPI, '
                             'using key \'{}\''.format(opts['identity']))
                else:
                    log.info('Uploading signed source distribution to PyPI '
                             'using default identity')
            else:
                log.info('Uploading unsigned source distribution to PyPI')

            log.debug('Running {}'.format(args))
            ve.check_output(
                args,
                cwd=td,
            )
