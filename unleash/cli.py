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
@click.option('--debug', '-d', 'loglevel', flag_value=logbook.DEBUG)
@click.option('--quiet', '-q', 'loglevel', flag_value=logbook.WARNING)
@click.option('--root', '-r', default='.',
              type=click.Path(exists=True, file_okay=False, dir_okay=True,
              resolve_path=True),
              help='Path to git repository to use.')
@click.option('--dry-run', '-n', is_flag=True)
@click.version_option()
@click.pass_obj
def cli(unleash, root, loglevel, batch, **kwargs):
    if loglevel is None:
        loglevel = logbook.INFO

    NullHandler().push_application()
    ColorizedStderrHandler(format_string='{record.message}',
                           level=loglevel).push_application()

    opts = {
        'interactive': not batch,
        'root': root,
    }

    opts.update(kwargs)

    unleash.set_global_opts(root, opts)
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
@click.option('--ref', '-r', default=None,
              help='Branch/Tag/Commit to publish. By default, use newest '
                   'tag by commit date.')
@click.pass_obj
def publish(unleash, ref, **kwargs):
    unleash.opts.update(kwargs)
    unleash.publish(ref)


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
