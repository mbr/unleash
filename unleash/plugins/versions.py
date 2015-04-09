from click import Option


PLUGIN_NAME = 'versions'


def setup(cli):
    cli.commands['release'].params.append(Option(
        ['--dev-version', '-d'],
        help='Set new development version to this. If not given, '
             'auto-increment the release-version.'
    ))

    cli.commands['release'].params.append(Option(
        ['--release-version', '-v'],
        help='Set the release version to this. If not given, will be '
             'auto-detected from setup.py.'
    ))


def collect_release_info(ctx):
    commit = ctx.commit
    opts = ctx.app.opts

    release_version = dev_version = None

    # first, determine release version
    if opts['release_version']:
        release_version = opts['release_version']

    if opts['dev_version']:
        dev_version = opts['dev_version']

    ctx.info['release_version'] = release_version
    ctx.info['dev_version'] = dev_version
