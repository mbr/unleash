from click import Option

from .utils_tree import require_file
from .utils_assign import replace_assign

PLUGIN_NAME = 'docs'
PLUGIN_DEPENDS = ['versions']


def setup(cli):
    cli.params.append(Option(
        ['--doc-dir', '-D'], default='docs',
        help='Default directory in which to look for docs.',
    ))


def collect_info(ctx):
    opts = ctx['opts']

    # for now, we support only a single docs dir
    doc_dir = opts['doc_dir']

    ctx['info']['doc_dir'] = doc_dir
    if not ctx['commit'].path_exists(doc_dir):
        ctx['issues'].warn(
            'No documentation folder found.',
            'Your commit does not contain a folder ''docs/''. No docs will be '
            'built for this release. To fix this, create the folder containing '
            'Sphinx-documentation.')
        ctx['info']['doc_dir'] = None


def prepare_release(ctx):
    info = ctx['info']
    if not info['doc_dir']:
        ctx['log'].debug('No doc dir, not building docs.')
        return

    conf_fn = info['doc_dir'].rstrip('/') + '/conf.py'
    conf = require_file(
        ctx, conf_fn, 'Could not find doc''s conf.py',
        'Could not find conf.py in your documentation path ({}). Please check '
        'that if there is a Sphinx-based documentation in that directory.'
        .format(ctx['info']['doc_dir']))

    conf = replace_assign(conf, 'version', info['release_version_short'])
    conf = replace_assign(conf, 'release', info['release_version'])

    ctx['commit'].set_path_data(conf_fn, conf)
