import os
import subprocess
import sys

from click import Option
from six.moves import shlex_quote
from .utils_tree import in_tmpexport


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
    cli.commands['publish'].params.append(Option(
        ['--gpg-binary'], default='gpg',
        help='Path to git binary to use.',
    ))
    cli.commands['publish'].params.append(Option(
        ['--gpg-homedir'], default=DEFAULT_GPG_HOMEDIR,
        help='Path to gpg homedir (default: {}).'.format(DEFAULT_GPG_HOMEDIR),
    ))


def collect_info(ctx):
    info = ctx['info']

    py = sys.executable
    if not py:
        ctx['issues'].error('Could not determine Python executable',
                            'unleash could not (through sys.executable) '
                            'determine the path to your Python interpreter. '
                            'This is required for launching other ')

    info['python'] = py


def publish_release(ctx):
    log = ctx['log']
    opts = ctx['opts']
    info = ctx['info']
    py = info['python']

    with in_tmpexport(ctx['commit']) as td:
        if opts['dry_run']:
            log.info('Creating source distribution, no upload (dry-run)')
            subprocess.check_output(
                [py, 'setup.py', 'sdist'],
                cwd=td,
            )
        else:

            args = [py, 'setup.py',
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
                             'using default identity.')
            else:
                log.info('Uploading unsigned source distribution to PyPI.')

            log.debug('Running {}'.format(args))
            subprocess.check_output(
                args,
                cwd=td,
            )
