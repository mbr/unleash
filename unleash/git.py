from datetime import datetime
import os
from stat import S_ISLNK, S_ISDIR, S_ISREG
import time

from dateutil.tz import tzlocal
from dulwich.objects import S_ISGITLINK, Blob, Commit
import logbook

from .version import find_assign, replace_assign

log = logbook.Logger('git')


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


def prepare_commit(repo, parent_commit_id, new_version, author, message):
    objects_to_add = []

    log.debug('Preparing new commit for version %s based on %s' % (
        new_version, parent_commit_id,
    ))
    tree = repo.object_store[repo.object_store[parent_commit_id].tree]

    # get setup.py
    setuppy_mode, setuppy_id = tree['setup.py']
    setuppy = repo.object_store[setuppy_id]

    release_setup = Blob.from_string(replace_assign(setuppy.data, 'version',
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
