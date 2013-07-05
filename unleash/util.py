import contextlib
import os
import subprocess
import sys

import logbook

log = logbook.Logger('util')


@contextlib.contextmanager
def dirch(dir):
    prev = os.getcwd()
    os.chdir(dir)
    yield
    os.chdir(prev)


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
