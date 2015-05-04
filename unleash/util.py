from contextlib import contextmanager
import os
import subprocess

import click
import logbook
from tempdir import TempDir
from unleash import opts
import virtualenv


log = logbook.Logger('util')


class VirtualEnv(object):
    def __init__(self, path):
        self.path = path

    @property
    def pip(self):
        return self.get_binary('pip')

    @property
    def python(self):
        return self.get_binary('python')

    def check_output(self, *args, **kwargs):
        env = {}
        env.update(kwargs.pop('env', {}))

        env['VIRTUAL_ENV'] = self.path
        env['PATH'] = os.pathsep.join([
            os.path.join(self.path, 'bin'),
            env.get('PATH', os.environ.get('PATH', ''))
        ])
        kwargs['env'] = env

        return subprocess.check_output(*args, **kwargs)

    def get_binary(self, name):
        return os.path.join(self.path, 'bin', name)

    def pip_install(self, *pkgs):
        return self.check_output([
            self.pip,
            'install',
        ] + list(pkgs))

    @classmethod
    def create(cls, path):
        virtualenv.create_environment(path)
        return cls(path)

    @classmethod
    @contextmanager
    def temporary(cls):
        with TempDir() as tmpdir:
            yield cls.create(tmpdir)

    def __str__(self):
        return '{}({!r})'.format(self.__class__.__name__, self.path)


def checked_output(cmd, *args, **kwargs):
    try:
        log.debug('run %s' % ' '.join(cmd))
        return subprocess.check_output(
            cmd, *args, stderr=subprocess.STDOUT, **kwargs
        )
    except subprocess.CalledProcessError as e:
        log.error('Error calling external process.\n%s' % e.output)
        raise


def run_user_shell(self, **kwargs):
    return subprocess.call(os.environ['SHELL'], env=os.environ, **kwargs)


def confirm_prompt(text, default=True, abort=True, **kwargs):
    if opts['interactive']:
        return click.confirm(text, default=default, abort=abort, **kwargs)
    return True
