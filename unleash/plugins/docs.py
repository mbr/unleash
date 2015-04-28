import os
import re
import subprocess

from click import Option
from tempdir import TempDir

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
    cli.params.append(Option(
        ['--sphinx-strict/--no-sphinx-strict'], default=True,
        help='Turn sphinx warnings into errors (default: True).'
    ))


def collect_info(ctx):
    opts = ctx['opts']

    # for now, we support only a single docs dir
    doc_dir = opts['doc_dir']

    ctx['info']['doc_dir'] = doc_dir
    if not ctx['commit'].path_exists(doc_dir):
        ctx['issues'].warn(
            'No documentation folder found',
            'Your commit does not contain a folder ''docs/''. No docs will be '
            'built for this release. To fix this, create the folder containing '
            'Sphinx-documentation.')
        ctx['info']['doc_dir'] = None
    else:
        ctx['info']['doc_conf'] = doc_dir.rstrip('/') + '/conf.py'

    conf = _get_doc_conf(ctx)

    if conf:
        theme_pkgs = ctx['opts']['sphinx_styles']
        if not theme_pkgs:
            theme_pkgs = IMPORT_THEME_RE.findall(conf)
        ctx['info']['sphinx_theme_pkgs'] = theme_pkgs


def _get_doc_conf(ctx):
    if not ctx['info']['doc_dir']:
        ctx['log'].debug('No doc dir, not building or updating docs')
        return

    return require_file(
        ctx, ctx['info']['doc_conf'], 'Could not find doc''s conf.py',
        'Could not find conf.py in your documentation path ({}). Please check '
        'that if there is a Sphinx-based documentation in that directory.'
        .format(ctx['info']['doc_dir'])
    )


def _set_doc_version(ctx, version, version_short):
    info = ctx['info']
    conf = _get_doc_conf(ctx)
    if not conf:
        return

    ctx['log'].info('Updating documentation version (now {})'.format(version))
    conf = replace_assign(conf, 'version', version_short)
    conf = replace_assign(conf, 'release', version)

    ctx['commit'].set_path_data(info['doc_conf'], conf)


def sphinx_build(ctx, ve, srcdir, outdir):
    info = ctx['info']
    sphinx_args = [
        ve.get_binary('sphinx-build'),
        '-b', 'html',    # build html
        # the following options don't hurt, but should not be
        # necessary as we are building in a clean temp dir
        '-E',            # don't use saved environment
        '-a'             # always write all files
    ]

    if ctx['opts']['sphinx_strict']:
        sphinx_args.extend(['-W', '-n'])

    sphinx_args.extend([
        os.path.join(srcdir, *info['doc_dir'].split('/')),  # src
        outdir,  # dest
    ])

    ctx['log'].debug('Running sphinx: {}'.format(sphinx_args))
    ve.check_output(sphinx_args)


def sphinx_install(ctx, ve):
    theme_pkgs = ctx['info']['sphinx_theme_pkgs']
    ctx['log'].debug('Will try to install the following theme packages: {}'
                     .format(theme_pkgs))

    # install sphinx and required theme packages
    ve.pip_install('sphinx', *theme_pkgs)


def prepare_release(ctx):
    info = ctx['info']
    _set_doc_version(ctx,
                     info['release_version'],
                     info['release_version_short'])


IMPORT_THEME_RE = re.compile(r'import\s+(sphinx\w*theme\w*)\b')


def lint_release(ctx):
    conf = _get_doc_conf(ctx)
    if not conf:
        return

    ctx['log'].info('Checking documentation builds cleanly')

    # create doc virtualenv
    with VirtualEnv.temporary() as ve, TempDir() as outdir:
        try:
            sphinx_install(ctx, ve)

            # ensure documentation builds cleanly
            with in_tmpexport(ctx['commit']) as srcdir:
                ve.pip_install(srcdir)

                sphinx_build(ctx, ve, srcdir, outdir)

        except subprocess.CalledProcessError as e:
            ctx['issues'].error(
                'Error building documentation:\n{}'.format(e)
            )


def prepare_dev(ctx):
    info = ctx['info']
    _set_doc_version(ctx,
                     info['dev_version'],
                     info['dev_version_short'])
