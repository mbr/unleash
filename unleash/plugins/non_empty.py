PLUGIN_NAME = 'non-empty'


def lint_release(ctx):
    if not ctx['commit'].tree.items():
        ctx['issues'].report('Commit is empty.', 'error')
