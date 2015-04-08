PLUGIN_NAME = 'docs'


def lint(ctx):
    # for now, we enforce a single docs dir
    docs_dir = 'docs'

    if not ctx.commit.path_exists(docs_dir):
        ctx.report(
            'docs', 'No documentation folder found.',
            suggestion='Your commit does not contain a folder ''docs/''. No '
                       'docs will be built for this release. To fix this, '
                       'create the folder containing Sphinx-documentation.')
