import click
import logbook
from logbook.more import ColorizedStderrHandler
from logbook.handlers import NullHandler

from .exc import UnleashError
from .plugin import PluginGraph
from .unleash import Unleash


log = logbook.Logger('cli')


@click.group()
@click.option('--batch', '-b', default=False, is_flag=True,
              help='Do not ask for confirmation before committing changes.')
@click.option('--debug', '-d', is_flag=True)
@click.option('--root', '-r', default='.',
              type=click.Path(exists=True, file_okay=False, dir_okay=True,
              resolve_path=True),
              help='Path to git repository to use.')
@click.version_option()
@click.pass_obj
def cli(unleash, root, debug, batch, **kwargs):
    # setup logging
    loglevel = logbook.INFO
    if debug:
        loglevel = logbook.DEBUG

    NullHandler().push_application()
    ColorizedStderrHandler(format_string='{record.message}',
                           level=loglevel).push_application()

    opts = {
        'interactive': not batch
    }

    opts.update(kwargs)

    unleash.set_global_opts(root, debug, opts)
    log.debug('Plugin order: {}'.format(unleash.plugins.resolve_order()))


@cli.command()
@click.option('--author', '-a', default=None,
              help='Author string for commits (uses git configured settings '
                   'per default')
@click.option('--inspect', '-i', is_flag=True, default=False,
              help='After processing, check out the commit interactively in a '
                   'shell.')
@click.option('--lint/--no-lint', '-l/-T', 'run_tests', default=True,
              help='Lint before releasing (default: enabled).')
@click.option('--ref', '-r', default='master',
              help='Branch/Tag/Commit to release.')
@click.pass_obj
def release(unleash, ref, **kwargs):
    unleash.opts.update(kwargs)
    unleash.create_release(ref)


@cli.command()
@click.option('--no-sign', '-S', 'sign', default=True, is_flag=True,
              help='Turn off code signing.')
@click.option('--tag', '-t',
              help='Tag to publish. Default is the latest tag created.')
@click.pass_obj
def publish(unleash, **kwargs):
    unleash.publish(**kwargs)


def main():
    try:
        plugins = PluginGraph()
        plugins.collect_plugins()
        plugins.notify('setup', cli)

        # instantiate application object
        unleash = Unleash(plugins)

        cli(obj=unleash)
    except UnleashError as e:
        log.critical(e)
