#!/usr/bin/env python
import os

from dulwich.repo import Repo

import logbook
from tempdir import TempDir
import virtualenv

from .util import dirch, checked_output, confirm
from .exc import ReleaseError
from .version import NormalizedVersion, find_version
from .git import export_to_dir, prepare_commit

log = logbook.Logger('unleash')


def action_create_release(args, repo):
    refname = 'refs/heads/%s' % args.branch
    if not refname in repo.refs:
        raise ValueError('Could not find %s' % refname)

    commit_id = repo.refs[refname]
    tree = repo.object_store[repo.object_store[commit_id].tree]
    log.debug('tree found: %s' % tree.id)

    # retrieve version from setup.py
    try:
        setuppy_mode, setuppy_id = tree['setup.py']
        setuppy = repo.object_store[setuppy_id]
    except KeyError:
        raise KeyError('setup.py not found in repository root')

    # find the version in setup.py
    version = find_version(setuppy.data, 'version')
    log.debug('Version on branch is %s' % version)

    if args.release_version is None:
        release_version = version.copy()
        release_version.drop_extras()

        if release_version == version:
            release_version.increment()
    else:
        release_version = NormalizedVersion(args.release_version)

    if args.dev_version is None:
        dev_version = release_version.copy()
        dev_version.increment()
        dev_version.set_dev_version()
    else:
        dev_version = NormalizedVersion(args.dev_version)

    log.debug('Release version %s' % release_version)
    log.debug('Next dev version %s' % dev_version)
    confirm('Release version %s, increase dev version to %s?' % (
        release_version, dev_version,
    ))

    msg_release = ('Release version %s.%s' % (release_version,
                                              args.commit_footer))
    msg_dev = ('Increased version to %s after release of %s.%s'
               % (dev_version, release_version, args.commit_footer))

    # prepare the commits
    release_commit, release_tree, release_objs = prepare_commit(
        repo, commit_id, release_version, args.author, msg_release
    )
    dev_commit, dev_tree, dev_objs = prepare_commit(
        repo, commit_id, dev_version, args.author, msg_dev
    )

    objects_to_add = []
    objects_to_add.extend(release_objs)
    objects_to_add.extend(dev_objs)

    for obj in objects_to_add:
        log.debug('Stored %r' % obj)
        repo.object_store.add_object(obj)

    # release is stored, but refs are not updated yet
    with TempDir() as src_tmpdir, TempDir() as venv_tmpdir:
        log.info('Creating new virtualenv...')
        log.debug(venv_tmpdir.name)
        virtualenv.create_environment(venv_tmpdir.name, use_distribute=True)

        log.info('Checking out release commit...')
        log.debug(src_tmpdir.name)
        export_to_dir(repo, release_commit.id, src_tmpdir.name)

        log.info('Creating source distribution...')
        with dirch(src_tmpdir.name):
            pip = os.path.join(venv_tmpdir.name, 'bin', 'pip')
            python = os.path.join(venv_tmpdir.name, 'bin', 'python')
            log.debug('PIP: %s' % pip)
            log.debug('Python: %s' % python)

            checked_output([python, 'setup.py', 'sdist'])
            dist_files = os.listdir(os.path.join(src_tmpdir.name, 'dist'))
            if not len(dist_files) == 1:
                raise ReleaseError('Extra files in dist-dir: %r' % dist_files)

            # we've built a valid package
            pkgfn = os.path.join(src_tmpdir.name, 'dist', dist_files[0])
            log.info('Successfully built %s' % pkgfn)

            # change into venv dir, so we try to install without the source
            # dir present
            with dirch(venv_tmpdir.name):
                # install into virtualenv
                log.info('Trying install into virtualenv...')
                checked_output([pip, 'install', pkgfn])

            # package installs fine, all is well
            log.info('Running tests...')
            checked_output([python, 'setup.py', 'test'])

    tag_refname = 'refs/tags/%s' % release_version
    confirm('Release commits created OK, tag %s and update %s?' % (
        tag_refname, refname)
    )

    # update heads
    log.info('Setting %s to %s' % (refname, dev_commit.id))
    repo.refs[refname] = dev_commit.id
    log.info('Setting %s to %s' % (tag_refname, release_commit.id))
    repo.refs[tag_refname] = release_commit.id


def main():
    import argparse

    from logbook.more import ColorizedStderrHandler
    from logbook.handlers import NullHandler

    from . import __version__

    default_footer = ('\n\nCommit using `unleash %s <'
                      'http://pypi.python.org/pypi/unleash>`_.'
                      % __version__
                      )

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
    create_release = sub.add_parser('create-release')
    create_release.add_argument('-b', '--branch', default='master')
    create_release.add_argument('-v', '--release-version', default=None)
    create_release.add_argument('-d', '--dev-version', default=None)
    create_release.add_argument('-F', '--no-footer', default=default_footer,
                                dest='commit_footer', action='store_const',
                                const='',
                                help='Do not output footer on commit messages.'
                                )

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

    return func(args=args, repo=repo)
