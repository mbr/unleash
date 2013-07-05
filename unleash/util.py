import contextlib
import os
import subprocess

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
