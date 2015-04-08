import click
import logbook
from logbook.more import ColorizedStderrHandler
from logbook.handlers import NullHandler

from .exc import UnleashError
from .plugin import collect_plugins, notify_plugins
from .unleash import Unleash


log = logbook.Logger('cli')


@click.group()
@click.option('--root', '-r', default='.',
              type=click.Path(exists=True, file_okay=False, dir_okay=True,
              resolve_path=True),
              help='Package root directory.')
@click.option('--batch', '-b', default=False, is_flag=True,
              help='Do not ask for confirmation before committing changes to '
              'anything.')
@click.option('--debug', '-d', is_flag=True)
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


@cli.command()
@click.option('--author', '-a', default=None,
              help='Author string for commits (uses git configured settings '
                   'per default')
@click.option('--inspect', '-i', is_flag=True, default=False,
              help='After processing, check out the commit interactively in a '
                   'shell.')
@click.option('--package-name', '-p',
              help='The name of the package to be packaged.')
@click.option('--dev-version', '-d',
              help='Set new development version to this.')
@click.option('--release-version', '-v',
              help='Set released version to this.')
@click.option('--lint/--no-lint', '-l/-T', 'run_tests', default=True,
              help='Lint before releasing (default: enabled).')
@click.argument('ref')
@click.pass_obj
def release(unleash, ref, **kwargs):
    unleash.opts.update(kwargs)
    unleash.create_release(ref)


@cli.command()
@click.argument('ref')
@click.pass_obj
def lint(unleash, ref, **kwargs):
    unleash.opts.update(kwargs)
    unleash.lint(ref)


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
        plugins = collect_plugins()
        notify_plugins(plugins, 'setup', cli)

        # instantiate application object
        unleash = Unleash(plugins)

        cli(obj=unleash)
    except UnleashError as e:
        log.critical(e)
