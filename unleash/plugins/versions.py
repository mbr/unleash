from click import Option
from versio.version import Version

from unleash import log, opts, issues, commit, info
from .utils_assign import find_assign, replace_assign
from .utils_tree import require_file

PLUGIN_NAME = 'versions'


def require_setup_py():
    return require_file(
        'setup.py',
        'No setup.py found',
        'The version could not determined because no setup.py file was found. '
        'Either supply a release version explicity or make sure setup.py '
        'exists in the root of the repository.'
    )


def setup(cli):
    cli.commands['release'].params.append(Option(
        ['--dev-version', '-d'],
        help='Set new development version to this. If not given, '
             'auto-increment the release-version.'
    ))

    cli.commands['release'].params.append(Option(
        ['--release-version', '-v'],
        help='Set the release version to this. If not given, will be '
             'auto-detected from setup.py.'
    ))

    cli.params.append(Option(
        ['--package-dir', '-p'], multiple=True,
        help='Directories in which packages can be found (used to update '
             '__version__ variables. Can be given multiple times.'
    ))


def _shorten_version(version):
    v = Version(str(version))
    v.parts = [v.parts[0]] + [None] * 4

    return v


def _set_commit_version(version):
    # Steps
    # 1. Replace commit message
    # 2. Replace version in setup.py
    # 3. Replace version in PKGNAME/__init__.py

    setup_py = require_setup_py()
    log.info('Updating setup.py and package version ({})'.format(version))

    # update setup.py
    commit.set_path_data('setup.py', replace_assign(
        setup_py,
        'version',
        version,
    ))

    # update PKGNAME/__init__.py files
    for fn in info['init_files']:
        # replace version info
        commit.set_path_data(fn, replace_assign(
            commit.get_path_data(fn),
            '__version__',
            version,
        ))


def collect_info():
    release_version = opts.get('release_version')
    dev_version = opts.get('dev_version')

    setup_py = require_setup_py()

    try:
        if release_version is None:
            # try extracting version info
            try:
                release_version = find_assign(setup_py, 'version')
            except ValueError as e:
                issues.error(
                    e,
                    'There was an issue extracting the version number from '
                    'setup.py. Please make sure there is only a single '
                    'version= assignment in that file.')

            log.debug('Release version automatically determined from setup.py')
        else:
            log.debug('Release version given on commandline.')

        # parse release version string
        release_version = _shorten_version(release_version)

        if dev_version is None:
            # if we're given no dev version, we try to create one by
            # incrementing the release version
            dev_version = Version(str(release_version))
            dev_version.bump('release')
            dev_version.bump('dev')
        else:
            # parse dev version string
            dev_version = Version(dev_version)
    except TypeError as e:
        issues.error(
            'Bad version number: {}'.format(e),
            'The version number "{}" is not a version number that can be '
            'understood by distutils.\n\n'
            'Please correct the different version number and try again.'
            .format(e))

    # get package name
    try:
        pkg_name = find_assign(setup_py, 'name')
    except ValueError as e:
        issues.error(
            e,
            'Could not extract package name from setup.py. Please make sure '
            'there is only a single name= expression in that file.')

    info['pkg_name'] = pkg_name
    info['release_version'] = str(release_version)
    info['dev_version'] = str(dev_version)

    # create the short versions
    info['release_version_short'] = str(_shorten_version(release_version))
    info['dev_version_short'] = str(_shorten_version(dev_version))

    # use provided package dirs or auto-detected one from setup.py
    pkg_paths = set(opts['package_dir'])
    if not pkg_paths:
        pkg_paths = set([info['pkg_name'],
                         info['pkg_name'].replace('-', '_')])

    log.debug('Package paths: {}'.format(pkg_paths))
    init_files = [path + '/__init__.py' for path in pkg_paths]

    init_files = filter(commit.path_exists, init_files)

    if not init_files:
        issues.warn(
            'No __init__.py files found for packages.',
            'While looking for package __init__.py files to update version '
            'information in, none were found. This most often happens if your '
            'package contains only modules or is not named after its primary '
            'Python package.')

    info['init_files'] = init_files


def prepare_release():
    # update commit message
    commit.message = u'Release version {}'.format(info['release_version'])

    _set_commit_version(info['release_version'])


def prepare_dev():
    commit.message = (u'Start developing version {} (after release of {})'
                      .format(info['dev_version'], info['release_version']))

    _set_commit_version(info['dev_version'])
