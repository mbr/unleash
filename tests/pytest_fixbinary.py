import shutilwhich
from shutil import which

import pytest


def binary(name, scope='session', **kwargs):
    @pytest.fixture(scope=scope, **kwargs)
    def _():
        path = which(name)

        if not path:
            pytest.skip('Skipping test; missing binary: {}'.format(path))

        return path

    return _
