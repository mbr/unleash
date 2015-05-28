from unleash import info, log, issues, commit


PLUGIN_NAME = 'travis'
PLUGIN_DEPENDS = ['tox_tests']

_TRAVIS_FILE = '.travis.yml'


def lint_release():
    log.info('Checking travis integration')

    if not info['tox_tests']:
        log.debug('Skipping travis integration, no tox tests found')
    else:
        if not commit.path_exists(_TRAVIS_FILE):
            issues.warn(
                'No .travis.yml found',
                'Your release is using tox based testing, but you have not '
                'enabled continuous integration using travis. This is easily '
                'done by adding a {} file.'.format(_TRAVIS_FILE))
