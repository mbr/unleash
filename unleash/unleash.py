from contextlib import contextmanager
from pprint import pformat
import os
import subprocess
import time

import click
from dulwich.repo import Repo
from dulwich.index import build_index_from_tree
from logbook import Logger
from tempdir import TempDir

from .exc import InvocationError, PluginError
from .git import export_tree, MalleableCommit, ResolvedRef, get_local_timezone
from .issues import IssueCollector

log = Logger('unleash')


class Unleash(object):
    def _confirm_prompt(self, text, default=True, abort=True, **kwargs):
        if self.opts['interactive']:
            click.confirm(text, default=default, abort=abort, **kwargs)

    @contextmanager
    def _checked_out(self, tree):
        with TempDir() as tmpdir:
            export_tree(self.repo.object_store.__getitem__,
                        self.repo[tree],
                        tmpdir)
            yield tmpdir

    def _create_child_commit(self, parent_ref):
        opts = self.opts

        parent = ResolvedRef(self.repo, parent_ref)

        if not parent.is_definite:
            raise InvocationError('{} is ambiguous: {}'.format(
                parent.ref, parent.full_name
            ))

        if not parent.found:
            raise InvocationError('Could not resolve "{}"'.format(parent.ref))

        # prepare the release commit
        commit = MalleableCommit.from_existing(
            self.repo, parent.id
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

        now = int(time.time())
        ltz = get_local_timezone(now)

        commit.author_time = now
        commit.author_timezone = ltz

        commit.commit_time = now
        commit.commit_timezone = ltz

        commit.parent_ids = [parent.id]

        return commit

    def __init__(self, plugins=[]):
        self.plugins = plugins

    def _perform_step(self, ctx, signal_name, issues):
        ctx['issues'] = issues.channel(signal_name)

        log.debug('begin: {}'.format(signal_name))
        begin = time.time()
        self.plugins.notify(signal_name, ctx=ctx)
        duration = time.time() - begin
        log.debug('end: {}, took {:.4f}s'.format(signal_name, duration))

    def create_release(self, ref):
        try:
            opts = self.opts
            base_ref = ResolvedRef(self.repo, ref)
            log.debug(
                'Base ref: {} ({})'.format(base_ref.full_name, base_ref.id)
            )

            orig_tree = base_ref.get_object().tree
            rcommit = self._create_child_commit(ref)
            rissues = IssueCollector(log=log)
            info = {}

            # create context
            rcontext = {
                'commit': rcommit,
                'opts': opts,
                'info': info,
                'log': log,
                'ref': base_ref,
            }

            self._perform_step(rcontext, 'collect_info', rissues)
            log.debug('info: {}'.format(
                pformat(rcontext['info']))
            )

            self._perform_step(rcontext, 'prepare_release', rissues)
            self._perform_step(rcontext, 'lint_release', rissues)

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
            self._perform_step(dcontext, 'prepare_dev', dissues)

            if opts['dry_run']:
                log.info('Not saving created commits. Dry-run successful.')
                return

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

            # if our release commit formed from a branch, we set that branch
            # to our new dev commit
            assert base_ref.is_definite and base_ref.found
            if not base_ref.is_ref or\
                    not base_ref.full_name.startswith('refs/heads'):
                log.warning('Release commit does not originate from a branch; '
                            'dev commit will not be reachable.')
                log.info('Dev commit: {}'.format(dev_hash))
            else:
                self.repo.refs[base_ref.full_name] = dev_hash

                # change the branch to point at our new dev commit
                log.info('{}: {}'.format(
                    base_ref.full_name, dev_hash
                ))

                self._update_working_copy(base_ref, orig_tree)
        except PluginError:
            # just abort, error has been logged already
            log.debug('Exiting due to PluginError')
            return

    def _update_working_copy(self, base_ref, orig_tree):
        head_ref = ResolvedRef(self.repo, 'HEAD')
        if not head_ref.is_definite or not head_ref.is_symbolic\
                or not head_ref.target == base_ref.full_name:
            log.info('HEAD is not a symbolic ref to {}, leaving your '
                     'working copy untouched.')
            return

        if not self.repo.has_index():
            log.info('Repository has no index, not updating working copy.')
            return

        index = self.repo.open_index()

        changes = list(index.changes_from_tree(
            self.repo.object_store,
            orig_tree,
        ))

        if changes:
            log.warning('There are staged changes in your index. Will not '
                        'update working copy.\n\n'
                        'You will need to manually change your HEAD to '
                        '{}.'.format(base_ref.id))
            return

        # reset the index to the new dev commit
        self._confirm_prompt(
            'Do you want to reset your index to the new dev commit and check '
            'it out? Unsaved changes to your working copy may be overwritten!'
        )
        log.info('Resetting index and checking out dev commit.')
        build_index_from_tree(
            self.repo.path,
            self.repo.index_path(),
            self.repo.object_store,
            base_ref.get_object().tree,
        )

    def publish(self, ref):
        if ref is None:
            tags = sorted(
                (t for t in self.repo.refs.as_dict().iteritems() if
                 t[0].startswith('refs/tags')),
                key=lambda (_, sha): self.repo[sha].commit_time,
                reverse=True,
            )

            if not tags:
                log.error('Could not find a tag to publish.')
                return

            ref = tags[0][0]

        pref = ResolvedRef(self.repo, ref)
        pcommit = MalleableCommit.from_existing(self.repo, pref.id)
        log.debug('Release tag: {}'.format(pcommit))

        pissues = IssueCollector(log=log)
        pcontext = {
            'commit': pcommit,
            'opts': self.opts,
            'info': {},
            'log': log,
            'ref': pref,
        }

        try:
            self._perform_step(pcontext, 'collect_info', pissues)
            log.debug('info: {}'.format(pformat(pcontext['info'])))

            self._perform_step(pcontext, 'publish_release', pissues)
        except PluginError:
            log.debug('Exiting due to PluginError')
            return

    def run_user_shell(self, **kwargs):
        return subprocess.call(os.environ['SHELL'], env=os.environ, **kwargs)

    def set_global_opts(self, root, opts=None):
        self.opts = opts or {}
        self.root = root

        self.repo = Repo(root)
        self.gitconfig = self.repo.get_config_stack()
