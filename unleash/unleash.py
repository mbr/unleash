import os

from blinker import signal
import click
from dulwich.repo import Repo
from dulwich.objects import Commit
from logbook import Logger
from tempdir import TempDir

from . import plugin_base, plugins
from .exc import ReleaseError, InvocationError
from .git import prepare_commit, resolve, export_tree
from .issues import IssueCollector
from .version import NormalizedVersion, find_version

log = Logger('unleash')


class LintOperation(IssueCollector):
    def __init__(self, app, commit):
        super(LintOperation, self).__init__()
        self.app = app
        self.commit = commit

    def run(self):
        self.issues = []

        # at this point, we know it's a commit. check out into temporary folder
        with TempDir() as self.tmpdir:
            export_tree(self.app.repo.object_store.__getitem__,
                        self.app.repo[self.commit.tree],
                        self.tmpdir)

            # now we run all linting plugins
            self.app.do_lint.send(self.app, lint=self)


class Unleash(object):
    default_footer = u'\n\n[commit by unleash {}]'
    release_msg = u'Release version {}.{}'
    dev_msg = u'Increased version to {} after release of {}.{}'

    # signals
    do_lint = signal('do_lint')

    def _confirm_prompt(self, text, default=True, abort=True, **kwargs):
        if self.interactive:
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

    def set_global_opts(self, root, batch, debug):
        self.root = root
        self.interactive = not batch
        self.debug = debug

        self.repo = Repo(root)
        self.config = self.repo.get_config_stack()

        # discover and load plugins
        self.plugin_source = plugin_base.make_plugin_source(
            searchpath=[os.path.dirname(plugins.__file__)]
        )

        with self.plugin_source:
            for plugin_name in self.plugin_source.list_plugins():
                log.debug('Loading plugin: {}'.format(plugin_name))
                plugin = self.plugin_source.load_plugin(plugin_name)
                plugin.setup(self)

    def lint(self, ref):
        commit = self._resolve_commit(ref)

        op = LintOperation(self, commit)
        op.run()

    def create_release(self, author, branch, package_name, release_version,
                       dev_version, run_tests, no_footer):
        if no_footer:
            footer = ''
        else:
            from . import __version__
            footer = self.default_footer.format(__version__)

        # detect author
        if author is None:
            author = '{} <{}>'.format(
                self.config.get('user', 'name'),
                self.config.get('user', 'email'),
            )

        # create ref for branch to release
        refname = 'refs/heads/{}'.format(branch).encode('ascii')
        if not refname in self.repo.refs:
            raise ReleaseError('Could not find %s' % refname)

        # find tree of commit
        commit = self.repo[refname]
        tree = self.repo[commit.tree]
        log.debug('tree found: %s' % tree.id)

        # determine version:
        # retrieve version from setup.py, use version in there as the
        # canonical version, unless specified otherwise
        try:
            setuppy_mode, setuppy_id = tree['setup.py']
            setuppy = self.repo[setuppy_id]
        except KeyError:
            raise ReleaseError('setup.py not found in repository root')
        version = find_version(setuppy.data, 'version')

        # release version defaults to canonical version
        if release_version is None:
            release_version = version.copy()
            release_version.drop_extras()
        else:
            release_version = NormalizedVersion(release_version)

        # dev version defaults to incremented release version
        if dev_version is None:
            dev_version = release_version.copy()
            dev_version.increment()
            dev_version.set_dev_version()
        else:
            dev_version = NormalizedVersion(dev_version)
        log.debug('Release: {}, Dev: {}, setup.py: {}'.format(
            release_version, dev_version, version,
        ))

        # ask user for confirmation, last chance to check if versions are
        # correct
        self._confirm_prompt('Release version {}, increase dev version to {}?'
                             .format(release_version, dev_version))

        # user confirmed, prepare the commits
        msg_release = self.release_msg.format(release_version, footer)
        msg_dev = self.dev_msg.format(dev_version, release_version, footer)


        # prepare the commits. this alters the trees without checking them
        # out
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

    def not_implemented():
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
