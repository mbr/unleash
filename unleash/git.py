from datetime import datetime
import os
from stat import S_ISLNK, S_ISDIR, S_ISREG, S_IFDIR
import time

from dateutil.tz import tzlocal
from dulwich.objects import S_ISGITLINK, Blob, Commit, Tree
import logbook
from stuf.collects import ChainMap

from .version import find_assign, replace_assign

log = logbook.Logger('git')


def add_path_to_tree(repo, tree, path, obj_mode, obj_id):
    parts = path.split('/')
    objects_to_update = []

    def _add(tree, parts):
        if len(parts) == 1:
            tree.add(parts[0], obj_mode, obj_id)
            objects_to_update.append(tree)
            return tree.id

        # there are more parts left
        subtree_name = parts.pop(0)

        # existing subtree?
        subtree_mode, subtree_id = tree[subtree_name]
        subtree = repo[subtree_id]
        # will raise KeyError if the parent directory does not exist

        # add remainder to subtree
        tree.add(subtree_name, subtree_mode, _add(subtree, parts))

        # update tree
        objects_to_update.append(tree)

    _add(tree, parts)
    return objects_to_update


def diff_tree(repo, tree_id, path=None):
    # FIXME: code a proper diff function, add to dulwich?
    if path is None:
        path = repo.path

    for entry in repo[tree_id].iteritems():
        fpath = os.path.join(path, entry.path)
        if not os.path.exists(fpath):
            return True  # an entry that should exist does not exist

        if S_ISGITLINK(entry.mode):
            raise NotImplementedError('Does not support submodules')
        elif S_ISDIR(entry.mode):
            if diff_tree(repo, entry.sha, fpath):
                return True  # a subdir differs
        elif S_ISLNK(entry.mode):
            raise NotImplementedError('Symlinks currently not supported')
        elif S_ISREG(entry.mode):
            with open(fpath, 'rb') as f:
                b = Blob.from_string(f.read())
                if not b.id == entry.sha:
                    log.debug('File %s differs' % fpath)
                    return True
        else:
            raise ValueError('Cannot deal with mode of %s' % entry)

    return False


def export_to_dir(repo, commit_id, output_dir):
    tree_id = repo[commit_id].tree
    export_tree(repo, tree_id, output_dir)


def export_tree(repo, tree_id, output_dir):
    # we assume output_dir exists and is empty
    if os.listdir(output_dir):
        raise ValueError('Directory %s not empty' % output_dir)

    for entry in repo[tree_id].iteritems():
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
            os.symlink(repo[entry.sha].data, output_path)
        elif S_ISREG(entry.mode):
            with open(output_path, 'wb') as out:
                for chunk in repo[entry.sha].chunked:
                    out.write(chunk)
            log.debug('wrote %s' % output_path)
        else:
            raise ValueError('Cannot deal with mode of %s' % entry)


class MalleableCommit(object):
    def __init__(self, repo, author=u'', message=u'', parent_ids=[], tree=None,
                 committer=None, commit_time=None, author_time=None,
                 commit_timezone=None, author_timezone=None,
                 encoding='UTF-8'):
        now = int(time.time())

        # calculate local timezone. must be done each time, due to DST
        _tz_offset = tzlocal().utcoffset(datetime.utcfromtimestamp(now))
        LOCAL_TIMEZONE = _tz_offset.days * 24 * 60 * 60 + _tz_offset.seconds

        self.repo = repo
        self.encoding = encoding
        self.parent_ids = parent_ids
        self.message = message

        self.author = author
        self.committer = author if committer is None else committer

        # times default to now
        self.author_time = author_time if author_time is not None else now
        self.commit_time = commit_time if commit_time is not None else now

        # the default timezone is the local timezone
        self.commit_timezone = (commit_timezone if commit_timezone is not None
                                else LOCAL_TIMEZONE)
        self.author_timezone = (author_timezone if author_timezone is not None
                                else LOCAL_TIMEZONE)

        # FIXME: empty tree on new commit?
        self.tree = tree

        self.new_objects = {}

        # chain used for looking up items, may include uncommitted ones
        self._lookup_chain = ChainMap(self.new_objects, self.repo.object_store)

    # FIXME: add methods for checkout into folder

    @classmethod
    def from_parent(cls, repo, parent_id):
        parent = repo[parent_id]

        nc = cls(repo, parent_ids=[parent_id])
        nc.tree = repo[parent.id]

        return nc

    @classmethod
    def from_existing(cls, repo, commit_id):
        commit = repo[commit_id]
        encoding = commit.encoding or 'UTF-8'
        return cls(
            repo,
            author=commit.author,
            message=commit.message.decode(encoding),
            parent_ids=commit.parents,
            committer=commit.committer,
            commit_time=commit.commit_time,
            author_time=commit.author_time,
            commit_timezone=commit.commit_timezone,
            author_timezone=commit.author_timezone,
            encoding=encoding,
            tree=repo[commit.tree],
        )

    def _to_commit(self):
        new_commit = Commit()
        new_commit.parents = self.parent_ids

        new_commit.tree = self.tree
        new_commit.author = self.author
        new_commit.committer = self.committer

        new_commit.author_time = self.author_time
        new_commit.commit_time = self.commit_time

        new_commit.commit_timezone = self.commit_timezone
        new_commit.author_timezone = self.author_timezone

        new_commit.encoding = self.encoding
        new_commit.message = self.message.encode(self.encoding)

        return new_commit

    def set_path_data(self, path, data, mode=0100644):
        blob = Blob.from_string(data)
        self.new_objects[blob.id] = blob

        return self.set_path_id(path, blob.id, mode)

    def set_path_id(self, path, id, mode=0100644):
        # we use regular "/" split here, as dulwich uses the same method
        parts = path.split('/')

        self.tree = self._path_add(self.tree, parts, id, mode)
        self.new_objects[self.tree.id] = self.tree

    def _path_add(self, tree, parts, id, mode):
        if len(parts) == 1:
            fn = parts[0]

            # add id and remember altered tree
            tree.add(fn, mode, id)
            return tree

        # there are more parts left
        subtree_name = parts[0]

        try:
            subtree_mode, subtree_id = tree[subtree_name]
            if not S_ISDIR(subtree_mode):
                subtree = None  # if it's a regular file, we overwrite it
            else:
                subtree = self._lookup_chain[subtree_id]
        except KeyError:
            subtree = None
            subtree_mode = S_IFDIR

        if subtree is None:
            subtree = Tree()

        # alter subtree and add to our tree
        old_subtree_id = subtree.id
        subtree = self._path_add(subtree, parts[1:], id, mode)

        # only store if the subtree actually changed
        if subtree.id != old_subtree_id:
            self.new_objects[subtree.id] = subtree
            tree.add(subtree_name, subtree_mode, subtree.id)

        return tree

    def get_path_id(self, path):
        return self._lookup(path)[1]

    def get_path_data(self, path):
        obj = self._lookup_chain[self.get_path_id(path)]

        if hasattr(obj, 'data'):
            return obj.data

    def get_path_mode(self, path):
        return self._lookup(path)[0]

    def save(self):
        # generate the commit
        commit = self._to_commit()
        self.new_objects[commit.id] = commit

        # instead of adding all new objects, we just add reachable ones
        ids_to_add = set()
        ids_to_add.add(commit.id)

        q = [commit.tree.id]
        while q:
            cur = q.pop()
            if not cur in self.new_objects:
                # already in repo
                continue

            ids_to_add.add(cur)

            # if it is a tree, also add children
            cur_obj = self.new_objects[cur]
            if isinstance(cur_obj, Tree):
                # add children
                for name, mode, sha in cur_obj.iteritems():
                    q.append(sha)

        # add all collected objects
        for id in ids_to_add:
            self.repo.object_store.add_object(self.new_objects[id])

    def _lookup(self, path):
        # construct a lookup chain that
        return self.tree.lookup_path(self._lookup_chain.__getitem__, path)


def prepare_commit(repo, parent_commit_id, new_version, author, message,
                   pkg_name=None):
    objects_to_add = set()

    # look up tree from previous commit
    tree = repo[repo[parent_commit_id].tree]

    # get setup.py
    setuppy_mode, setuppy_id = tree['setup.py']
    setuppy = repo[setuppy_id]

    # get __init__.py's
    if pkg_name == None:
        pkg_name = find_assign(setuppy.data, 'name')

    log.debug('Package name is %s' % pkg_name)
    pkg_init_fn = '%s/__init__.py' % pkg_name

    try:
        (pkg_init_mode, pkg_init_id) =\
            tree.lookup_path(repo.object_store.__getitem__, pkg_init_fn)
    except KeyError:
        log.error('Did not find package "%s"' % pkg_init_fn)
        raise
    else:
        log.debug('Found %s' % pkg_init_fn)
        pkg_init = repo[pkg_init_id]
        release_pkg_init = Blob.from_string(
            replace_assign(pkg_init.data, '__version__', str(new_version))
        )
        objects_to_add.add(release_pkg_init)

    release_setup = Blob.from_string(replace_assign(setuppy.data, 'version',
                                     str(new_version)))

    # get documentation's conf.py
    try:
        # FIXME: 'docs/' should not be hardcoded here, also duplicates
        # stuff from build_docs
        docconf_fn = 'docs/conf.py'

        docconf_mode, docconf_id = tree.lookup_path(
            repo.object_store.__getitem__, docconf_fn)
        log.debug('Found %s' % docconf_fn)
    except KeyError:
        log.warning('No documentation found (missing %s)' % docconf_fn)
    else:
        # got docs, update version numbers in those as well
        docconf = repo[docconf_id]
        release_docconf_data = docconf.data
        new_shortver = new_version.copy()
        new_shortver.drop_extras()

        release_docconf_data = replace_assign(
            release_docconf_data, 'version', str(new_shortver)
        )
        release_docconf_data = replace_assign(
            release_docconf_data, 'release', str(new_version)
        )

        release_docconf = Blob.from_string(release_docconf_data)

        objects_to_add.add(release_docconf)

        # after this point, lookup_path cannot be used anymore
        objects_to_add.update(
            add_path_to_tree(
                repo, tree, docconf_fn, docconf_mode, release_docconf.id
            ))

    # tree modifications need to be delayed, if done above will affect searches
    objects_to_add.update(
        add_path_to_tree(
            repo, tree, pkg_init_fn, pkg_init_mode, release_pkg_init.id
        ))
    tree.add('setup.py', setuppy_mode, release_setup.id)
    objects_to_add.add(release_setup)
    objects_to_add.add(tree)

    new_commit = create_commit(
        parent_ids=[parent_commit_id],
        tree_id=tree.id,
        author=author,
    )

    objects_to_add.add(new_commit)

    # check objects
    for obj in objects_to_add:
        obj.check()

    return new_commit, tree, objects_to_add
