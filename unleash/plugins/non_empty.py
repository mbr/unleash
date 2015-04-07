import os

from blinker import signal


def on_lint(app, lint):
    if os.listdir(lint.tmpdir) == []:
        lint.warn('non-empty', 'Commit is empty.')


def setup(unleash):
    signal('do_lint').connect(on_lint)
