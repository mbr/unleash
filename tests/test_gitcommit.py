import os
import subprocess

from dulwich.repo import Repo
import pytest
from tempdir import TempDir
from unleash.git import MalleableCommit, export_tree, resolve

from pytest_fixbinary import binary


git_binary = binary('git')


@pytest.yield_fixture
def git_repo(git_binary):
    with TempDir() as tmpdir:
        subprocess.check_call(['git', 'init', tmpdir])
        yield tmpdir


@pytest.fixture
def dummy_repo(git_binary, git_repo):
    fn = os.path.join(git_repo, 'foo.txt')
    dn = os.path.join(git_repo, 'sub/dir')
    fdn = os.path.join(dn, 'dest.txt')

    # create dummy files
    os.makedirs(dn)
    open(fn, 'w').write('bar')
    open(fdn, 'w').write('baz')

    # add to git repo
    subprocess.check_call([git_binary, 'add', fn, fdn], cwd=git_repo)
    subprocess.check_call([git_binary, 'commit', '-m', 'test commit'],
                          cwd=git_repo)

    return git_repo


@pytest.fixture
def repo(dummy_repo):
    return Repo(dummy_repo)


def test_git_repo(git_repo):
    assert os.path.exists(os.path.join(git_repo, '.git'))


def test_dummy_repo(dummy_repo):
    pass


def test_commit_reading(repo):
    master = repo.refs['refs/heads/master']

    c = MalleableCommit.from_existing(repo, master)

    assert c.encoding == 'UTF-8'
    assert c.parent_ids == []
    assert c.message == u'test commit\n'

    assert c.get_path_data('foo.txt') == 'bar'
    assert c.get_path_mode('foo.txt') == 0100644

    assert c.get_path_data('sub/dir/dest.txt') == 'baz'
    assert c.get_path_mode('sub/dir/dest.txt') == 0100644

    with pytest.raises(KeyError):
        assert c.get_path_data('does.not.exist')

    # directories return None and have just the dir flag set
    assert c.get_path_data('sub') is None
    assert c.get_path_mode('sub') == 0040000


def test_commit_id_setting(repo):
    master = repo.refs['refs/heads/master']

    c = MalleableCommit.from_existing(repo, master)
    baz = c.get_path_id('sub/dir/dest.txt')

    old_tree_id = c.tree.id

    c.set_path_id('foo.txt', baz)
    assert c.get_path_data('foo.txt') == 'baz'
    assert c.tree.id != old_tree_id


def test_commit_content_writing(repo):
    master = repo.refs['refs/heads/master']

    c = MalleableCommit.from_existing(repo, master)
    c.set_path_data('foo.txt', 'NEW')
    assert c.get_path_data('foo.txt') == 'NEW'

    c.set_path_data('new_stuff.txt', 'two')
    assert c.get_path_data('new_stuff.txt') == 'two'

    c.set_path_data('with/path/new', 'three')
    assert c.get_path_data('with/path/new') == 'three'
    assert c.get_path_data('with/path') is None
    assert c.get_path_data('with') is None


def test_commit_overwrites_files_with_dirs(repo):
    master = repo.refs['refs/heads/master']

    c = MalleableCommit.from_existing(repo, master)
    assert c.get_path_data('foo.txt') == 'bar'

    c.set_path_data('foo.txt/bla', 'NEW')
    assert c.get_path_data('foo.txt/bla') == 'NEW'
    assert c.get_path_data('foo.txt') is None


def test_commit_changes_mode(repo):
    master = repo.refs['refs/heads/master']

    c = MalleableCommit.from_existing(repo, master)
    c.set_path_data('xyz.txt', 'NEW', mode=0100755)
    assert c.get_path_data('xyz.txt') == 'NEW'
    assert c.get_path_mode('xyz.txt') == 0100755


def test_commit_persists_changes(dummy_repo, repo):
    master = repo.refs['refs/heads/master']

    c = MalleableCommit.from_existing(repo, master)
    c.set_path_data('xyz.txt', 'NEW', mode=0100755)
    tree_id = c.tree.id
    c.save()

    r = Repo(dummy_repo)
    t = r[tree_id]

    b_id = t['xyz.txt'][1]
    assert r[b_id].data == 'NEW'


def test_export_to_existing(repo):
    master = repo.refs['refs/heads/master']
    c = repo[master]

    with TempDir() as outdir:
        export_tree(repo.object_store.__getitem__, repo[c.tree], outdir)

        # check if all files are present
        assert os.path.exists(os.path.join(outdir, 'foo.txt'))
        assert os.path.exists(os.path.join(outdir, 'sub', 'dir', 'dest.txt'))
        assert 'bar' == open(os.path.join(outdir, 'foo.txt')).read()


def test_export_to_uncommitted(repo):
    master = repo.refs['refs/heads/master']

    c = MalleableCommit.from_existing(repo, master)

    c.set_path_data('xyz.txt', 'NEW', mode=0100755)
    c.set_path_data('foo.txt', 'overwritten')

    with TempDir() as outdir:
        c.export_to(outdir)

        # check if all files are present
        assert os.path.exists(os.path.join(outdir, 'foo.txt'))
        assert os.path.exists(os.path.join(outdir, 'sub', 'dir', 'dest.txt'))
        assert 'overwritten' == open(os.path.join(outdir, 'foo.txt')).read()
        assert 'NEW' == open(os.path.join(outdir, 'xyz.txt')).read()


def test_my_resolve(repo):
    master = repo.refs['refs/heads/master']
    c = repo[master]

    assert [c] == resolve(repo, repo.__getitem__, 'master')
    assert [] == resolve(repo, repo.__getitem__, 'meh')


def test_path_exists(repo):
    master = repo.refs['refs/heads/master']

    c = MalleableCommit.from_existing(repo, master)

    assert c.path_exists('foo.txt')
    assert not c.path_exists('xx')
