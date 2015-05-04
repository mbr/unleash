from unleash import commit, issues, info, log

PLUGIN_NAME = 'license'
PLUGIN_DEPENDS = ['egg_info']


def lint_release():
    log.info('Checking license information')
    if not commit.path_exists('LICENSE'):
        issues.warn(
            'No LICENSE file found in package root',
            'Your source package does not include a LICENSE file. To avoid '
            'confusion and allow reuse by others, your source files should '
            'include a file named LICENSE containing your licensing '
            'conditions.')

    if not info['egg_info'].license:
        issues.warn(
            'No license information found in egg_info',
            'The resulting egg-info contained no information about your '
            'license. This is usually a result of a missing \'license=\' '
            'parameter in your setup function in setup.py.'
        )
