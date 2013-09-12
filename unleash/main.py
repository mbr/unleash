#!/usr/bin/env python
import os

from dulwich.repo import Repo

import logbook

from .util import dirch, checked_output, confirm, tmp_virtualenv, tmp_checkout
from .exc import ReleaseError
from .version import NormalizedVersion, find_version
from .git import prepare_commit, diff_tree

log = logbook.Logger('unleash')


def build_docs(src, python, pip):
    DOCS = 'docs'
    docs_dir = os.path.join(src, DOCS)
    build_dir = os.path.join(src, '_unleash-docs-build')

    if not os.path.exists(docs_dir):
        log.warning("No documentation found (missing '%s' dir)" % DOCS)
    else:
        with dirch(src):
            log.info('Building documentation')
            checked_output([pip, 'install', 'sphinx'])
            checked_output([python, 'setup.py', 'build_sphinx',
                            '--source-dir', docs_dir,
                            '--build-dir', build_dir])
        return build_dir


def action_create_release(args, repo):
    refname = 'refs/heads/%s' % args.branch
    if not refname in repo.refs:
        raise ValueError('Could not find %s' % refname)

    commit = repo[refname]
    tree = repo[commit.tree]
    log.debug('tree found: %s' % tree.id)

    # retrieve version from setup.py
    try:
        setuppy_mode, setuppy_id = tree['setup.py']
        setuppy = repo[setuppy_id]
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
        repo, commit.id, release_version, args.author, msg_release,
        args.package_name,
    )
    dev_commit, dev_tree, dev_objs = prepare_commit(
        repo, commit.id, dev_version, args.author, msg_dev, args.package_name,
    )

    objects_to_add = []
    objects_to_add.extend(release_objs)
    objects_to_add.extend(dev_objs)

    for obj in objects_to_add:
        log.debug('Stored %r' % obj)
        repo.object_store.add_object(obj)

    # release is stored, but refs are not updated yet
    with tmp_checkout(repo, release_commit.id) as src,\
            tmp_virtualenv() as venv:

        log.info('Creating source distribution...')
        with dirch(src):
            pip = os.path.join(venv, 'bin', 'pip')
            python = os.path.join(venv, 'bin', 'python')
            log.debug('PIP: %s' % pip)
            log.debug('Python: %s' % python)

            checked_output([python, 'setup.py', 'sdist'])
            dist_files = os.listdir(os.path.join(src, 'dist'))
            if not len(dist_files) == 1:
                raise ReleaseError('Extra files in dist-dir: %r' % dist_files)

            # we've built a valid package
            pkgfn = os.path.join(src, 'dist', dist_files[0])
            log.info('Successfully built %s' % pkgfn)

            # change into venv dir, so we try to install without the source
            # dir present
            with dirch(venv):
                # install into virtualenv
                log.info('Trying install into virtualenv...')
                checked_output([pip, 'install', pkgfn])

                # ensure docs can be built in release
                build_docs(src, python, pip)

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

    if not repo.bare:
        repo_prefix = 'ref: '

        # if HEAD points to the updated branch, update the index
        if not repo.refs.read_ref('HEAD') == repo_prefix + refname:
            log.warning('HEAD does not point to %s, but %s. Will not update '
                        'index.' % (refname, repo.refs.read_ref('HEAD')))
        elif not repo.has_index():
            log.warning('Repo has no index. Why?')
        else:
            index = repo.open_index()
            if [c for c in index.changes_from_tree(
                repo.object_store, repo[dev_commit.parents[0]].tree)
            ]:
                # the index has wasn't clean before
                log.warning('Index was not clean, not checking out new copy.')
            else:
                # FIXME: missing - check if working copy has changes
                log.warning('(not implemented): Should update index.')


def action_publish(args, repo):
    import verlib

    prefix = 'refs/tags/'
    if args.version is None:
        versions = []
        for tag in repo.refs.allkeys():
            tagname = tag[len(prefix):]
            if not tag.startswith(prefix):
                continue

            try:
                real_version = verlib.NormalizedVersion(tagname)
                if not str(real_version) == tagname:
                    log.warn('Invalid version tag %s' % tagname)
                versions.append(real_version)
            except verlib.IrrationalVersionError:
                log.debug('Ignoring tag %s, invalid version')

        if versions:
            args.version = str(sorted(versions, reverse=True)[0])

    log.debug('Passed version: %s' % args.version)
    if not args.version:
        raise ValueError('No version given and no version tag found.')

    commit = repo[prefix + args.version]
    log.info('Checking out %s (%s)...' % (args.version, commit.id))

    with tmp_checkout(repo, commit.id) as src, tmp_virtualenv() as venv:
        log.info('Uploading to PyPI...')
        with dirch(src):
            python = os.path.join(venv, 'bin', 'python')
            pip = os.path.join(venv, 'bin', 'pip')
            log.debug('Python: %s' % python)

            cmd = [python, 'setup.py', 'sdist', 'upload']
            if args.sign:
                cmd.extend(['-s', '-i', args.sign])
            checked_output(cmd)

            docs_build_dir = build_docs(src, python, pip)
            if docs_build_dir:
                # docs were built, upload them
                log.info('Uploading documentation')
                checked_output([pip, 'install', 'sphinx-pypi-upload'])
                cmd = [python, 'setup.py', 'upload_sphinx', '--upload-dir',
                       os.path.join(docs_build_dir, 'html')]
                checked_output(cmd)

    with dirch(repo.path):
        log.info('Pushing tag %s to origin using git...' % args.version)
        # FIXME: at some point, do this without git?
        checked_output(['git', 'push', 'origin', args.version])


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
