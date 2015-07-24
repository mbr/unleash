import click
import logbook
from logbook.more import ColorizedStderrHandler
from logbook.handlers import NullHandler
import os

from .exc import UnleashError
from .plugin import PluginGraph
from .boilerplate import Recipe
from .unleash import Unleash
from . import _context, opts


log = logbook.Logger('cli')


def umask_value(s):
    if s == 'off':
        return False
    val = int(s, 8)

    if val > 0o777 or val < 0:
        raise ValueError('Invalid umask')

    return val


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
@click.option('--umask', default='0022', type=umask_value)
@click.version_option()
@click.pass_context
def cli(ctx, root, loglevel, batch, umask, **kwargs):
    unleash = ctx.obj
    if loglevel is None:
        loglevel = logbook.INFO

    NullHandler().push_application()
    ColorizedStderrHandler(format_string='{record.message}',
                           level=loglevel).push_application()

    if not umask is False:
        log.debug('Setting umask to {:04o}'.format(umask))
        prev_umask = os.umask(umask)

        if prev_umask != umask:
            log.info('umask changed from {:04o} to {:04o}'.format(
                prev_umask, umask)
            )

    _context.push({
        'opts': {}
    })

    opts['interactive'] = not batch,
    opts['root'] = root
    opts.update(kwargs)

    if ctx.invoked_subcommand != 'boilerplate':
        unleash._init_repo()

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
    opts.update(kwargs)
    unleash.create_release(ref)


@cli.command()
@click.option('--ref', '-r', default=None,
              help='Branch/Tag/Commit to publish. By default, use newest '
                   'tag by commit date.')
@click.pass_obj
def publish(unleash, ref, **kwargs):
    opts.update(kwargs)
    unleash.publish(ref)


@cli.command()
@click.argument('recipe')
@click.option('-d', '--destination', default='.', type=click.Path())
def boilerplate(recipe, destination):
    rcp = Recipe(recipe)

    rcp.collect_answers()
    rcp.run(destination)


def main():
    try:
        with NullHandler().applicationbound():
            plugins = PluginGraph()
            plugins.collect_plugins()
            plugins.notify('setup', cli)

        # instantiate application object
        unleash = Unleash(plugins)

        cli(obj=unleash)
    except UnleashError as e:
        log.critical(e)
