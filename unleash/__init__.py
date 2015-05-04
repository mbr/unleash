__version__ = '0.7.0'


from contextlib import contextmanager
from functools import partial

from werkzeug.local import LocalStack, LocalProxy


def _lookup_context(name):
    top = _context.top
    if top is None:
        raise RuntimeError('No current context.')
    return top[name]


@contextmanager
def new_local_stack():
    nc = {} if _context.top is None else _context.top.copy()

    _context.push(nc)
    yield nc
    _context.pop()


_context = LocalStack()
log = LocalProxy(partial(_lookup_context, 'log'))
info = LocalProxy(partial(_lookup_context, 'info'))
issues = LocalProxy(partial(_lookup_context, 'issues'))
commit = LocalProxy(partial(_lookup_context, 'commit'))
opts = LocalProxy(partial(_lookup_context, 'opts'))
