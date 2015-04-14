import os
import subprocess

from click import Option

from unleash.util import VirtualEnv
from .utils_tree import require_file, in_tmpexport
from .utils_assign import replace_assign

PLUGIN_NAME = 'docs'
PLUGIN_DEPENDS = ['versions']


def setup(cli):
    cli.params.append(Option(
        ['--doc-dir', '-D'], default='docs',
        help='Default directory in which to look for docs.',
    ))
    cli.params.append(Option(
        ['--sphinx-styles'], multiple=True,
        help='Names of extra packages containing sphinx styles to install '
             'when building docs (default: auto-detect from conf.py).'
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


def _check_version_dir_present(ctx):
    if not ctx['info']['doc_dir']:
        ctx['log'].debug('No doc dir, not building or updating docs.')
        return False
    return True


def _set_doc_version(ctx, version, version_short):
    info = ctx['info']

    conf_fn = info['doc_dir'].rstrip('/') + '/conf.py'
    conf = require_file(
        ctx, conf_fn, 'Could not find doc''s conf.py',
        'Could not find conf.py in your documentation path ({}). Please check '
        'that if there is a Sphinx-based documentation in that directory.'
        .format(ctx['info']['doc_dir']))

    conf = replace_assign(conf, 'version', version_short)
    conf = replace_assign(conf, 'release', version)

    ctx['commit'].set_path_data(conf_fn, conf)


def prepare_release(ctx):
    if not _check_version_dir_present(ctx):
        return

    info = ctx['info']
    _set_doc_version(ctx,
                     info['release_version'],
                     info['release_version_short'])


def lint_release(ctx):
    if not _check_version_dir_present(ctx):
        return

    info = ctx['info']
    theme_pkgs = ctx['opts']['sphinx_styles']

    if not theme_pkgs:
        pass  # FIXME: auto-detect necessary doc packages

    # create doc virtualenv
    with VirtualEnv.temporary() as ve:
        ve.pip_install('sphinx', *theme_pkgs)

        # ensure documentation builds cleanly
        with in_tmpexport(ctx['commit']) as tmpdir:
            try:
                subprocess.check_output(
                    ['make', 'html'],
                    cwd=os.path.join(tmpdir, *info['doc_dir'].split('/'))
                )
            except subprocess.CalledProcessError as e:
                ctx['issues'].error(
                    'Error building documentation:\n{}'.format(e)
                )


def prepare_dev(ctx):
    if not _check_version_dir_present(ctx):
        return

    info = ctx['info']
    _check_version_dir_present(ctx)
    _set_doc_version(ctx,
                     info['dev_version'],
                     info['dev_version_short'])
