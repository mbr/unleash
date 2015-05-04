#!/usr/bin/env python
import os

import logbook

from .util import dirch, checked_output, tmp_virtualenv, tmp_checkout

log = logbook.Logger('unleash')


def build_docs(src, python, pip):
    DOCS = 'docs'
    docs_dir = os.path.join(src, DOCS)
    build_dir = os.path.join(src, '_unleash-docs-build')

    if not os.path.exists(docs_dir):
        log.warning("No documentation found (missing '%s' dir)" % DOCS)
    else:
        with dirch(src):
            log.info('Building documentation')
            checked_output([pip, 'install', 'sphinx', 'sphinx-readable-theme',
                            'sphinx_rtd_theme', 'sphinx-better-theme'])

            # make sure autodoc works
            checked_output([python, 'setup.py', 'develop'])

            checked_output([python, 'setup.py', 'build_sphinx',
                            '--source-dir', docs_dir,
                            '--build-dir', build_dir])
        return build_dir


def action_publish(args, repo):
    import verlib

    prefix = 'refs/tags/'
    if args.version is None:
        versions = []
        for tag in repo.refs.keys():
            tagname = tag[len(prefix):]
            if not tag.startswith(prefix):
                continue

            try:
                real_version = verlib.NormalizedVersion(tagname)
                if not str(real_version) == tagname:
                    log.warn('Invalid version tag %s' % tagname)
                versions.append(real_version)
            except verlib.IrrationalVersionError:
                log.debug('Ignoring tag %s, invalid version')

        if versions:
            args.version = str(sorted(versions, reverse=True)[0])

    log.debug('Passed version: %s' % args.version)
    if not args.version:
        raise ValueError('No version given and no version tag found.')

    commit = repo[prefix + args.version]
    log.info('Checking out %s (%s)...' % (args.version, commit.id))

    with tmp_checkout(repo, commit.id) as src, tmp_virtualenv() as venv:
        log.info('Uploading to PyPI...')
        with dirch(src):
            python = os.path.join(venv, 'bin', 'python')
            pip = os.path.join(venv, 'bin', 'pip')
            log.debug('Python: %s' % python)

            cmd = [python, 'setup.py', 'sdist', 'upload']
            if args.sign:
                cmd.extend(['-s', '-i', args.sign])
            checked_output(cmd)

            docs_build_dir = build_docs(src, python, pip)
            if docs_build_dir:
                # docs were built, upload them
                log.info('Uploading documentation')
                checked_output([pip, 'install', 'sphinx-pypi-upload'])
                cmd = [python, 'setup.py', 'upload_sphinx', '--upload-dir',
                       os.path.join(docs_build_dir, 'html')]
                checked_output(cmd)

    with dirch(repo.path):
        log.info('Pushing tag %s to origin using git...' % args.version)
        # FIXME: at some point, do this without git?
        checked_output(['git', 'push', 'origin', args.version])
