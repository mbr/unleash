from blinker import signal
import os


def on_lint(app, lint):
    if os.listdir(lint.tmpdir) == []:
        lint.report('non-empty', 'Commit is empty')


def setup(unleash):
    signal('do_lint').connect(on_lint)
