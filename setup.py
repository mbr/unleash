#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='unleash',
    version='0.6.0',
    description=('Creates release commits directly in git, unleashes them on '
                 'PyPI and pushes tags to github.'),
    long_description=read('README.rst'),
    author='Marc Brinkmann',
    author_email='git@marcbrinkmann.de',
    url='http://github.com/mbr/unleash',
    license='MIT',
    packages=find_packages(exclude=['test']),
    install_requires=['click>=4.0', 'dulwich', 'logbook', 'tempdir>=0.6',
                      'virtualenv>=1.10.1', 'python-dateutil', 'versio',
                      'stuf', 'pluginbase', 'networkx'],
    entry_points={
        'console_scripts': [
            'unleash = unleash.cli:main',
        ],
    }
)
