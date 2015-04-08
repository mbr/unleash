import click
import logbook
from logbook.more import ColorizedStderrHandler
from logbook.handlers import NullHandler

from .exc import UnleashError
from .unleash import Unleash

log = logbook.Logger('cli')


pass_unleash = click.make_pass_decorator(Unleash, ensure=True)


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
@pass_unleash
def cli(unleash, root, debug, batch):
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

    unleash.set_global_opts(root, debug, opts)


@cli.command('create-release')
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
@click.option('--footer/--no-footer', '-f/-F', default=False,
              help='Mark commits as created by unleash (default: disabled).')
@click.argument('ref')
@pass_unleash
def create_release(unleash, ref, **kwargs):
    unleash.opts.update(kwargs)
    unleash.create_release(ref)


@cli.command('lint')
@click.argument('ref')
@pass_unleash
def lint(unleash, ref, **kwargs):
    unleash.opts.update(kwargs)
    unleash.lint(ref)


@cli.command()
@click.option('--no-sign', '-S', 'sign', default=True, is_flag=True,
              help='Turn off code signing.')
@click.option('--tag', '-t',
              help='Tag to publish. Default is the latest tag created.')
@pass_unleash
def publish(unleash, **kwargs):
    unleash.publish(**kwargs)


def main():
    try:
        cli()
    except UnleashError as e:
        log.critical(e)
