PLUGIN_NAME = 'non-empty'


def lint(ctx):
    if not ctx.commit.tree.items():
        lint.report('non-empty', 'Commit is empty.')
