import os

PLUGIN_NAME = 'non-empty'


def lint(app, lint):
    if os.listdir(lint.tmpdir) == []:
        lint.report('non-empty', 'Commit is empty')
