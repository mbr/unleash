from contextlib import contextmanager

from tempdir import in_tempdir


def require_file(ctx, path, error, suggestion=None):
    # find setup.py
    if not ctx['commit'].path_exists(path):
        ctx['issues'].error(error, suggestion)

    return ctx['commit'].get_path_data(path)


@contextmanager
def in_tmpexport(commit):
    with in_tempdir() as tmpdir:
        commit.export_to(tmpdir)
        yield tmpdir
