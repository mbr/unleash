from datetime import datetime
import os
from stat import S_ISLNK, S_ISDIR, S_ISREG
import time

from dateutil.tz import tzlocal
from dulwich.objects import S_ISGITLINK, Blob, Commit
import logbook

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


def prepare_commit(repo, parent_commit_id, new_version, author, message):
    objects_to_add = set()

    log.debug('Preparing new commit for version %s based on %s' % (
        new_version, parent_commit_id,
    ))
    tree = repo[repo[parent_commit_id].tree]

    # get setup.py
    setuppy_mode, setuppy_id = tree['setup.py']
    setuppy = repo[setuppy_id]

    # get __init__.py's
    pkg_name = find_assign(setuppy.data, 'name')
    log.debug('Package name is %s' % pkg_name)
    pkg_init_fn = '%s/__init__.py' % pkg_name

    try:
        (pkg_init_mode, pkg_init_id) =\
            tree.lookup_path(repo.object_store.__getitem__, pkg_init_fn)
    except KeyError:
        log.debug('Did not find %s' % pkg_init_fn)
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
    objects_to_add.add(new_commit)

    # check objects
    for obj in objects_to_add:
        obj.check()

    return new_commit, tree, objects_to_add
