from blinker import signal


def on_lint(app, lint):
    print lint, lint.tmpdir


def setup(unleash):
    signal('do_lint').connect(on_lint)
