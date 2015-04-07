import os

from blinker import signal


def on_lint(app, lint):
    # for now, we enforce a single docs dir
    doc_dir = os.path.join(lint.tmpdir, 'docs')

    if not os.path.exists(doc_dir):
        lint.report(
            'docs', 'No documentation folder found.',
            suggestion='Your commit does not contain a folder ''docs/''. No '
                       'docs will be built for this release. To fix this, '
                       'create the folder containing Sphinx-documentation.')


def setup(unleash):
    signal('do_lint').connect(on_lint)
