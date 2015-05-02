from click import Option

from unleash import opts, log, commit
from unleash import __version__ as unleash_version


PLUGIN_NAME = 'footer'

# make sure version info is written first, so the footer does not get
# overwritten
PLUGIN_DEPENDS = ['versions']

FOOTER_FORMAT = u'\n[commit by unleash {}]\n'


def setup(cli):
    cli.commands['release'].params.append(Option(
        ['--footer/--no-footer', '-f/-F'], default=False,
        help='Add "created by unleash" footer (default: disabled).'
    ))

    cli.commands['release'].params.append(Option(
        ['--unleash-committer/--no-unleash-committer', '-c/-C'],
        default=True, help='Set the committer to unleash (default: enabled).'
    ))


def prepare_release():
    if not opts['footer'] and not opts['unleash_committer']:
        return

    log.info('Marking release as released by unleash')

    if opts['footer']:
        commit.message += FOOTER_FORMAT.format(unleash_version)
    if opts['unleash_committer']:
        commit.committer = 'unleash <{}>'.format(unleash_version)
