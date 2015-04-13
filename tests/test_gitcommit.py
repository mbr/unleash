import os
import subprocess

from dulwich.repo import Repo
import pytest
from tempdir import TempDir
from unleash.git import MalleableCommit, export_tree, ResolvedRef

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

    fn2 = fn + '2'
    open(fn2, 'w').write('second file')
    subprocess.check_call([git_binary, 'add', fn2], cwd=git_repo)
    subprocess.check_call([git_binary, 'commit', '-m', 'second test commit'],
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
    assert len(c.parent_ids) == 1
    assert c.message == u'second test commit\n'

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
    assert c.save()

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


def test_path_exists(repo):
    master = repo.refs['refs/heads/master']

    c = MalleableCommit.from_existing(repo, master)

    assert c.path_exists('foo.txt')
    assert not c.path_exists('xx')


def test_to_commit(repo):
    master = repo.refs['refs/heads/master']

    c = MalleableCommit.from_existing(repo, master)

    raw_commit = c.to_commit()
    assert raw_commit.tree == repo[master].tree


def test_ref_resolution_single_ref(repo):
    rr = ResolvedRef(repo, 'master')
    assert rr.is_definite
    assert rr.full_name == 'refs/heads/master'
    assert rr.type == 'ref'
    assert rr.is_ref
    assert not rr.is_object
    assert rr.get_object() == repo['refs/heads/master']
    assert rr.id == repo.refs['refs/heads/master']
    assert rr.found
    assert not rr.is_symbolic


def test_ref_resolution_nonexistant(repo):
    rr = ResolvedRef(repo, 'doesnotexist')
    assert rr.is_definite
    assert rr.full_name is None
    assert rr.type is None
    assert not rr.is_ref
    assert not rr.is_object
    assert rr.get_object() is None
    assert rr.id is None
    assert not rr.found
    assert not rr.is_symbolic


def test_ref_resolution_object(repo):
    master = repo.refs['refs/heads/master']

    assert len(master) == 40

    rr = ResolvedRef(repo, master)
    assert rr.is_definite
    assert rr.full_name == master
    assert rr.type == 'object'
    assert not rr.is_ref
    assert rr.is_object
    assert rr.get_object() == repo['refs/heads/master']
    assert rr.id == master
    assert rr.found
    assert not rr.is_symbolic


def test_ref_resolution_multiple_ref(repo):
    cur = repo[repo.refs['refs/heads/master']]
    master_tag = cur.parents[0]
    master_branch = cur.id

    # we add a tag "master"
    repo.refs['refs/tags/master'] = master_tag

    rr = ResolvedRef(repo, 'master')
    assert not rr.is_definite
    assert rr.full_name == ['refs/tags/master', 'refs/heads/master']
    assert rr.type == ['ref', 'ref']
    assert rr.is_ref
    assert not rr.is_object
    assert rr.get_object() == [repo['refs/tags/master'],
                               repo['refs/heads/master']]
    assert rr.id == [master_tag, master_branch]
    assert rr.found
    assert not rr.is_symbolic


def test_ref_resoltion_finds_head(repo):
    rr = ResolvedRef(repo, 'HEAD')

    assert rr.found
    assert rr.is_symbolic
    assert rr.target == 'refs/heads/master'
