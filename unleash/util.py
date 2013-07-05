import contextlib
import os
import subprocess
import sys

import logbook
from tempdir import TempDir
import virtualenv

log = logbook.Logger('util')


@contextlib.contextmanager
def dirch(dir):
    prev = os.getcwd()
    os.chdir(dir)
    yield
    os.chdir(prev)


@contextlib.contextmanager
def tmp_virtualenv():
    with TempDir() as tmpdir:
        log.info('Creating new virtualenv...')
        log.debug(tmpdir.name)
        virtualenv.create_environment(tmpdir.name, use_distribute=True)
        yield os.path.abspath(tmpdir.name)


def checked_output(cmd, *args, **kwargs):
    try:
        log.debug('run %s' % ' '.join(cmd))
        subprocess.check_output(cmd, *args, stderr=subprocess.STDOUT, **kwargs)
    except subprocess.CalledProcessError as e:
        log.error('Error calling external process.\n%s' % e.output)
        raise


def yesno(question):
    while True:
        inp = raw_input(question + ' [y/n]: ')

        if inp in ('y', 'Y', 'yes', 'YES'):
            return True
        elif inp in ('n', 'N', 'no', 'NO'):
            return False
        else:
            print 'Please answer \'yes\' or \'no\'.'


def confirm(question):
    if not yesno(question):
        log.warning('Aborted by user request.')
        sys.exit(1)
