#!/usr/bin/env python

from datetime import datetime
from dateutil.tz import tzlocal
import contextlib
import re
import os
import subprocess
import time

from dulwich.repo import Repo
from dulwich.objects import S_ISGITLINK, Blob, Commit
from stat import S_ISLNK, S_ISDIR, S_ISREG
import logbook
import verlib
from tempdir import TempDir
import virtualenv

log = logbook.Logger('unleash')


class ReleaseError(Exception):
    pass


@contextlib.contextmanager
def dirch(dir):
    prev = os.getcwd()
    os.chdir(dir)
    yield
    os.chdir(prev)


def get_local_tz_offset(ltz, now):
    offset = ltz.utcoffset(now)
    offset = abs(offset)

    return offset.days * 24 * 60 * 60 + offset.seconds, False


class NormalizedVersion(verlib.NormalizedVersion):
    def increment(self):
        main = list(self.parts[0])
        main[-1] += 1
        self.parts = (tuple(main), verlib.FINAL_MARKER, verlib.FINAL_MARKER)

    def set_dev_version(self, num=1):
        self.parts = (self.parts[0], verlib.FINAL_MARKER, ('dev%d' % num,))

    def drop_extras(self):
        main, prerel, postdev = self.parts
        self.parts = (main, verlib.FINAL_MARKER, verlib.FINAL_MARKER)

    def copy(self):
        return self.__class__(str(self))


def export_to_dir(repo, commit_id, output_dir):
    tree_id = repo.object_store[commit_id].tree
    export_tree(repo, tree_id, output_dir)


def export_tree(repo, tree_id, output_dir):
    # we assume output_dir exists and is empty
    if os.listdir(output_dir):
        raise ValueError('Directory %s not empty' % output_dir)

    for entry in repo.object_store[tree_id].iteritems():
        output_path = os.path.join(output_dir, entry.path)

        if S_ISGITLINK(entry.mode):
            raise ValueError('Does not support submodules')
        elif S_ISDIR(entry.mode):
            os.mkdir(output_path)  # mode parameter here is umasked, use chmod
            os.chmod(output_path, 0755)
            log.debug('created %s' % output_path)
            export_tree(repo, entry.sha, os.path.join(output_dir, output_path))
        elif S_ISLNK(entry.mode):
            log.debug('link %s' % output_path)
            os.symlink(repo.object_store[entry.sha].data, output_path)
        elif S_ISREG(entry.mode):
            with open(output_path, 'wb') as out:
                for chunk in repo.object_store[entry.sha].chunked:
                    out.write(chunk)
            log.debug('wrote %s' % output_path)
        else:
            raise ValueError('Cannot deal with mode of %s' % entry)


_quotes = "['|\"|\"\"\"]"
BASE_VERSION_PATTERN = r'(%s=\s*[ubr]?' + _quotes + r')(.*?)(' + _quotes + r')'


def find_version(data, varname):
    VERSION_RE = re.compile(BASE_VERSION_PATTERN % varname)

    if len(VERSION_RE.findall(data)) != 1:
        raise ValueError('Found multiple %s-strings.' % varname)

    return NormalizedVersion(verlib.suggest_normalized_version(
        VERSION_RE.search(data).group(2)
    ))


def replace_version(data, varname, new_version):
    VERSION_RE = re.compile(BASE_VERSION_PATTERN % varname)

    def repl(m):
        return m.group(1) + new_version + m.group(3)

    return VERSION_RE.sub(repl, data)


def prepare_commit(repo, parent_commit_id, new_version, author, message):
    objects_to_add = []

    log.debug('Preparing new commit for version %s based on %s' % (
        new_version, parent_commit_id,
    ))
    tree = repo.object_store[repo.object_store[parent_commit_id].tree]

    # get setup.py
    setuppy_mode, setuppy_id = tree['setup.py']
    setuppy = repo.object_store[setuppy_id]

    release_setup = Blob.from_string(replace_version(setuppy.data, 'version',
                                     str(new_version)))
    tree['setup.py'] = (setuppy_mode, release_setup.id)

    objects_to_add.append(release_setup)
    objects_to_add.append(tree)

    now = int(time.time())
    new_commit = Commit()
    new_commit.parents = [parent_commit_id]

    new_commit.tree = tree.id

    new_commit.author = author
    new_commit.committer = author

    new_commit.commit_time = now
    new_commit.author_time = now

    now = int(time.time())
    offset = tzlocal().utcoffset(datetime.utcfromtimestamp(now))
    timezone = offset.days * 24 * 60 * 60 + offset.seconds
    new_commit.commit_timezone = timezone
    new_commit.author_timezone = timezone

    new_commit.encoding = 'utf8'
    new_commit.message = message
    objects_to_add.append(new_commit)

    # check objects
    for obj in objects_to_add:
        obj.check()

    return new_commit, tree, objects_to_add


def checked_output(cmd, *args, **kwargs):
    try:
        log.debug('run %s' % ' '.join(cmd))
        subprocess.check_output(cmd, *args, stderr=subprocess.STDOUT, **kwargs)
    except subprocess.CalledProcessError as e:
        log.error('Error calling external process.\n%s' % e.output)
        raise


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
    log.info('Version on branch is %s' % version)

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

    log.info('Release version %s' % release_version)
    log.info('Next dev version %s' % dev_version)

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

    # update heads
    log.info('Setting %s to %s' % (refname, dev_commit.id))
    repo.refs[refname] = dev_commit.id
    tag_refname = 'refs/tags/%s' % release_version
    log.info('Setting %s to %s' % (tag_refname, release_commit.id))
    repo.refs[tag_refname] = release_commit.id


def main():
    import argparse

    from logbook.more import ColorizedStderrHandler
    handler = ColorizedStderrHandler()
    handler.push_application()

    default_footer = ('\n\nCommit using `unleash 0.1dev <'
                      'http://pypi.python.org/pypi/unleash>`_.')

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='action')
    parser.add_argument('-r', '--root', default=os.getcwd(),
                        type=os.path.abspath,
                        help='Root directory for package.')
    parser.add_argument('-a', '--author', default=None,
                        help='Author string for commits (uses git configured '
                             'settings per default')
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

    # first, determine current version
    repo = Repo(args.root)
    config = repo.get_config_stack()

    if args.author is None:
        args.author = '%s <%s>' % (
            config.get('user', 'name'), config.get('user', 'email')
        )

    func = globals()['action_' + args.action.replace('-', '_')]

    return func(args=args, repo=repo)


if __name__ == '__main__':
    main()
