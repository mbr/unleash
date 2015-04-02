import os
import subprocess

from dulwich.repo import Repo
import pytest
from tempdir import TempDir
from unleash.git import MalleableCommit

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
