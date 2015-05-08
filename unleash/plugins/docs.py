import os
import re
import subprocess

from click import Option
from tempdir import TempDir

from unleash import opts, info, commit, issues, log
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
    cli.commands['publish'].params.append(Option(
        ['--upload-docs/--no-upload-docs', '-d/-D'], default=True,
        help='Upload documentation to PyPI.'
    ))


def collect_info():
    # for now, we support only a single docs dir
    doc_dir = opts['doc_dir']

    info['doc_dir'] = doc_dir
    if not commit.path_exists(doc_dir):
        issues.warn(
            'No documentation folder found',
            'Your commit does not contain a folder ''docs/''. No docs will be '
            'built for this release. To fix this, create the folder containing '
            'Sphinx-documentation.')
        info['doc_dir'] = None
    else:
        info['doc_conf'] = doc_dir.rstrip('/') + '/conf.py'

    conf = _get_doc_conf()

    if conf:
        theme_pkgs = opts['sphinx_styles']
        if not theme_pkgs:
            theme_pkgs = IMPORT_THEME_RE.findall(conf)
        info['sphinx_theme_pkgs'] = theme_pkgs


def _get_doc_conf():
    if not info['doc_dir']:
        log.debug('No doc dir, not building or updating docs')
        return

    return require_file(
        info['doc_conf'], 'Could not find doc''s conf.py',
        'Could not find conf.py in your documentation path ({}). Please check '
        'that if there is a Sphinx-based documentation in that directory.'
        .format(info['doc_dir'])
    )


def _set_doc_version(version, version_short):
    conf = _get_doc_conf()
    if not conf:
        return

    log.info('Updating documentation version (now {})'.format(version))
    conf = replace_assign(conf, 'version', version_short)
    conf = replace_assign(conf, 'release', version)

    commit.set_path_data(info['doc_conf'], conf)


def sphinx_build(ve, srcdir, outdir):
    sphinx_args = [
        ve.get_binary('sphinx-build'),
        '-b', 'html',    # build html
        # the following options don't hurt, but should not be
        # necessary as we are building in a clean temp dir
        '-E',            # don't use saved environment
        '-a'             # always write all files
    ]

    if opts['sphinx_strict']:
        sphinx_args.extend(['-W', '-n'])

    sphinx_args.extend([
        os.path.join(srcdir, *info['doc_dir'].split('/')),  # src
        outdir,  # dest
    ])

    log.debug('Running sphinx: {}'.format(sphinx_args))
    ve.check_output(sphinx_args)


def sphinx_install(ve):
    theme_pkgs = info['sphinx_theme_pkgs']
    log.debug('Will try to install the following theme packages: {}'
              .format(theme_pkgs))

    # install sphinx and required theme packages
    ve.pip_install('sphinx', *theme_pkgs)


def prepare_release():
    _set_doc_version(info['release_version'],
                     info['release_version_short'])


IMPORT_THEME_RE = re.compile(r'import\s+(sphinx\w*theme\w*)\b')


def lint_release():
    conf = _get_doc_conf()
    if not conf:
        return

    log.info('Checking documentation builds cleanly')

    # create doc virtualenv
    with VirtualEnv.temporary() as ve, TempDir() as outdir:
        try:
            sphinx_install(ve)

            # ensure documentation builds cleanly
            with in_tmpexport(commit) as srcdir:
                ve.pip_install(srcdir)

                sphinx_build(ve, srcdir, outdir)

        except subprocess.CalledProcessError as e:
            issues.error(
                'Error building documentation:\n{}'.format(e)
            )


def prepare_dev():
    _set_doc_version(info['dev_version'],
                     info['dev_version_short'])


def publish_release():
    conf = _get_doc_conf()
    if not conf:
        return

    if opts['upload_docs']:
        log.info('Uploading documentation to PyPI')

    # create doc virtualenv
    with VirtualEnv.temporary() as ve, in_tmpexport(commit) as srcdir:
        try:
            sphinx_install(ve)
            ve.pip_install(srcdir)
            ve.check_output([
                ve.python, 'setup.py', 'upload_docs'
            ])
        except subprocess.CalledProcessError as e:
            issues.error(
                'Error building documentation:\n{}'.format(e)
            )
