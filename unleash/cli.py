import click
import logbook
from logbook.more import ColorizedStderrHandler
from logbook.handlers import NullHandler

from .exc import ReleaseError
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
def cli(unleash, **kwargs):
    # setup logging
    loglevel = logbook.INFO
    if kwargs['debug']:
        loglevel = logbook.DEBUG

    NullHandler().push_application()
    ColorizedStderrHandler(format_string='{record.message}',
                           level=loglevel).push_application()

    unleash.set_global_opts(**kwargs)


@cli.command('create-release')
@click.option('--author', '-a', default=None,
              help='Author string for commits (uses git configured settings '
                   'per default')
@click.option('--branch', '-b', default='master',
              help='Branch to cut the release from.')
@click.option('--package-name', '-p',
              help='The name of the package to be packaged.')
@click.option('--dev-version', '-d',
              help='Set new development version to this.')
@click.option('--release-version', '-v',
              help='Set released version to this.')
@click.option('--skip-tests', '-T', 'run_tests', default=True,
              flag_value=False, is_flag=True,
              help='Do not run tests if tests are found.')
@click.option('--no-footer', '-F', default=True, is_flag=False,
              help='Do not output footer on commit messages.')
@pass_unleash
def create_release(unleash, **kwargs):
    unleash.create_release(**kwargs)


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
    except ReleaseError as e:
        log.critical(e)
