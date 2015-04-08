from unleash import __version__ as unleash_version


PLUGIN_NAME = 'footer'

FOOTER_FORMAT = u'\n[commit by unleash {}]\n'


def prepare_release(ctx):
    if ctx.app.opts['footer']:
        ctx.commit.message += FOOTER_FORMAT.format(unleash_version)
