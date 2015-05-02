from contextlib import contextmanager

from tempdir import in_tempdir
from unleash import issues, commit


def require_file(path, error, suggestion=None):
    # find setup.py
    if not commit.path_exists(path):
        issues.error(error, suggestion)

    return commit.get_path_data(path)


@contextmanager
def in_tmpexport(commit):
    with in_tempdir() as tmpdir:
        commit.export_to(tmpdir)
        yield tmpdir
