from contextlib import contextmanager
from pprint import pformat
import os
import subprocess

import click
from dulwich.repo import Repo
from dulwich.objects import Commit
from logbook import Logger
from tempdir import TempDir

from .exc import ReleaseError, InvocationError, PluginError
from .git import resolve, export_tree, MalleableCommit
from .issues import IssueCollector

log = Logger('unleash')


class Unleash(object):
    def _confirm_prompt(self, text, default=True, abort=True, **kwargs):
        if self.opts['interactive']:
            click.confirm(text, default=default, abort=abort, **kwargs)

    def _resolve_commit(self, ref):
        objs = resolve(self.repo, self.repo.__getitem__, ref.encode('ascii'))
        log.debug('Resolved {!r} to {!r}'.format(ref, objs))

        commits = filter(lambda c: isinstance(c, Commit), objs)

        if not commits:
            raise InvocationError('Could not resolve "{}"'.format(ref))

        if len(commits) > 1:
            raise InvocationError('Ambiguous commit-ish "{}": {}'.format(
                ref, objs,
            ))

        return commits[0]

    @contextmanager
    def _checked_out(self, tree):
        with TempDir() as tmpdir:
            export_tree(self.repo.object_store.__getitem__,
                        self.repo[tree],
                        tmpdir)
            yield tmpdir

    def _create_child_commit(self, parent_ref):
        opts = self.opts

        # prepare the release commit
        commit = MalleableCommit.from_existing(
            self.repo, self._resolve_commit(parent_ref).id
        )

        # update author and such
        if opts['author'] is None:
            commit.author = '{} <{}>'.format(
                self.gitconfig.get('user', 'name'),
                self.gitconfig.get('user', 'email'),
            )
            commit.commiter = commit.author
        else:
            commit.author = opts['author']
            commit.committer = opts['author']

        return commit

    def __init__(self, plugins=[]):
        self.plugins = plugins

    def create_release(self, ref):
        try:
            opts = self.opts

            rcommit = self._create_child_commit(ref)
            rissues = IssueCollector(log=log)
            info = {}

            # create context
            rcontext = {
                'commit': rcommit,
                'opts': opts,
                'info': info,
                'issues': rissues.channel('collect'),
                'log': log,
            }

            # perform necessary release steps
            log.info('Collecting release information')
            self.plugins.notify('collect_info', ctx=rcontext)

            log.debug('Collected information:\n{}'.format(
                pformat(rcontext['info']))
            )

            log.info('Preparing release')
            rcontext['issues'] = rissues.channel('prepare_release')
            self.plugins.notify('prepare_release', ctx=rcontext)

            if opts['inspect']:
                log.info(unicode(rcommit))
                # check out to temporary directory
                with TempDir() as inspect_dir:
                    rcommit.export_to(inspect_dir)

                    log.info('You are being dropped into an interactive shell '
                             'inside a temporary checkout of the release '
                             'commit. No changes you make will persist. Exit '
                             'the shell to abort the release process.\n\n'
                             'Use "exit 2" to continue the release.')

                    status = self.run_user_shell(cwd=inspect_dir)

                if status != 2:
                    raise InvocationError(
                        'Aborting release, got exit code {} from shell.'.
                        format(status))

            log.info('Linting release')
            rcontext['issues'] = rissues.channel('lint')
            self.plugins.notify('lint_release', ctx=rcontext)

            # we're done with the release, now create the dev commit
            dcommit = self._create_child_commit(ref)
            dissues = IssueCollector(log=log)

            # update context
            dcontext = {
                'commit': dcommit,
                'release_commit': rcommit,
                'opts': opts,
                'info': info,
                'issues': dissues.channel('collect'),
                'log': log,
            }

            # creating development commit
            log.info('Creating development release')
            self.plugins.notify('prepare_dev', ctx=dcontext)

            # we've got both commits, now tag the release
            self._confirm_prompt(
                'Advance dev to {} and release {}?'
                .format(info['dev_version'], info['release_version'])
            )

            release_tag = 'refs/tags/{}'.format(info['release_version'])

            if release_tag in self.repo.refs:
                self._confirm_prompt(
                    'Repository already contains {}, really overwrite the tag?'
                    .format(release_tag),
                )

            release_hash = rcommit.save()

            log.info('{}: {}'.format(release_tag, release_hash))
            self.repo.refs[release_tag] = release_hash

            # save the dev commit
            dev_hash = dcommit.save()

            if not self._resolve_commit('HEAD') == self._resolve_commit(ref):
                log.warning('HEAD does not point at the same commit as '
                            'base commit. Not changing HEAD.')
            else:
                log.info('HEAD: {}'.format(dev_hash))
                # we change the HEAD commit
                self.repo.refs['HEAD'] = dev_hash
        except PluginError:
            # just abort, error has been logged already
            log.debug('Exiting due to PluginError')
            return

    def run_user_shell(self, **kwargs):
        return subprocess.call(os.environ['SHELL'], env=os.environ, **kwargs)

    def set_global_opts(self, root, debug=False, opts=None):
        self.opts = opts or {}
        self.root = root
        self.debug = debug

        self.repo = Repo(root)
        self.gitconfig = self.repo.get_config_stack()


    def ____():
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
                if args.run_tests:
                    if os.path.exists(os.path.join(src, 'tox.ini')):
                        log.info('Running tests (tox)...')
                        checked_output([pip, 'install', 'tox'])
                        tox = os.path.join(venv, 'bin', 'tox')
                        checked_output([tox])
                    else:
                        log.info('Running tests (setuptools)...')
                        checked_output([python, 'setup.py', 'test'])
                else:
                    log.warning('Skipping tests')

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
