#!/usr/bin/env python

import os

from dulwich.repo import Repo
from dulwich.objects import S_ISGITLINK
from stat import S_ISLNK, S_ISDIR, S_ISREG
import logbook

log = logbook.Logger('release')


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


def new_main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--root', default=os.getcwd(),
                        type=os.path.abspath,
                        help='Root directory for package.')
    args = parser.parse_args()

    # first, determine current version
    repo = Repo(args.root)

    # create temporary directory
    print 'project root', args.root

    export_to_dir(repo, repo.refs['refs/heads/master'], '/tmp/1')

if __name__ == '__main__':
    new_main()
