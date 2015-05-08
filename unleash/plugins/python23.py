from unleash import issues, info, log


PLUGIN_NAME = 'python23'
PLUGIN_DEPENDS = ['egg_info']


_PY2_CLASSIFIER = 'Programming Language :: Python :: 2'
_PY3_CLASSIFIER = 'Programming Language :: Python :: 3'


def lint_release():
    log.info('Checking Python2/3 classifiers')
    cs = info['egg_info'].classifiers
    if not cs:
        issues.warn(
            'No classifiers set in setup.py (missing Python 2/3 versioning)',
            'No classifiers have been set in the setup function of your '
            'package. These are required for automated tools to pick up '
            'python2/3 compatibility.'
        )
    else:
        if not _PY2_CLASSIFIER in cs and not _PY3_CLASSIFIER in cs:
            issues.warn(
                'No version classifiers found',
                'Your classifiers included neither {} nor {}. At least one '
                'of those is required to indicate compatiblity.')
