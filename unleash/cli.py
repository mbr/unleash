import logbook
import os

from dulwich.repo import Repo


log = logbook.Logger('cli')


def main():
    import argparse
    import sys

    from logbook.more import ColorizedStderrHandler
    from logbook.handlers import NullHandler

    from . import __version__

    default_footer = '\n\n(commit by unleash %s)' % __version__

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='action')
    parser.add_argument('-r', '--root', default=os.getcwd(),
                        type=os.path.abspath,
                        help='Root directory for package.')
    parser.add_argument('-a', '--author', default=None,
                        help='Author string for commits (uses git configured '
                             'settings per default')
    parser.add_argument('-b', '--batch', default=True, dest='interactive',
                        action='store_true',
                        help='Do not ask for confirmation before committing '
                             'changes to anything.')
    parser.add_argument('-d', '--debug', default=logbook.INFO, dest='loglevel',
                        action='store_const', const=logbook.DEBUG)
    parser.add_argument('--version', action='version',
                        version='%(prog)s ' + __version__)

    create_release = sub.add_parser('create-release')
    create_release.add_argument('-b', '--branch', default='master')
    create_release.add_argument('-v', '--release-version', default=None)
    create_release.add_argument('-d', '--dev-version', default=None)
    create_release.add_argument('-T', '--no-test', dest='run_tests',
                                action='store_false', default=True)
    create_release.add_argument('-F', '--no-footer', default=default_footer,
                                dest='commit_footer', action='store_const',
                                const='',
                                help='Do not output footer on commit messages.'
                                )
    create_release.add_argument('-n', '--package-name', default=None,
                                help='The name of the package to be packaged.')

    publish_release = sub.add_parser('publish')
    publish_release.add_argument('-s', '--sign')
    publish_release.add_argument('-v', '--version', default=None,
                                 help=('Name of the tag to publish. Defaults '
                                       'to the tag whose commit has the '
                                       'highest readable version.'))

    args = parser.parse_args()

    NullHandler().push_application()
    ColorizedStderrHandler(format_string='{record.message}',
                           level=args.loglevel).push_application()

    # first, determine current version
    repo = Repo(args.root)
    config = repo.get_config_stack()

    if args.author is None:
        args.author = '%s <%s>' % (
            config.get('user', 'name'), config.get('user', 'email')
        )

    func = globals()['action_' + args.action.replace('-', '_')]

    try:
        return func(args=args, repo=repo)
    except Exception as e:
        log.error(str(e))
        if args.loglevel == logbook.DEBUG:
            log.exception(e)
        sys.exit(1)
