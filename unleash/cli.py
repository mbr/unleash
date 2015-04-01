import click
from dulwich.repo import Repo
import logbook
from logbook.more import ColorizedStderrHandler
from logbook.handlers import NullHandler

log = logbook.Logger('cli')


pass_cfg = click.make_pass_decorator(dict, ensure=True)


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
@pass_cfg
def cli(cfg, root, batch, debug):
    cfg['DEBUG'] = debug
    cfg['ROOT'] = root
    cfg['INTERACTIVE'] = not batch
    cfg['REPO'] = Repo(root)
    cfg['GITCONFIG'] = cfg['REPO'].get_config_stack()

    # setup logging
    loglevel = logbook.INFO
    if debug:
        loglevel = logbook.DEBUG

    NullHandler().push_application()
    ColorizedStderrHandler(format_string='{record.message}',
                           level=loglevel).push_application()


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
@pass_cfg
def create_release(cfg, author, branch, package_name, release_version,
                   dev_version, run_tests, no_footer):
    if no_footer:
        footer = ''
    else:
        from . import __version__
        footer = '\n\n(commit by unleash {})'.format(__version__)

    # detect author
    if author is None:
        author = '{} <{}>'.format(
            cfg['GIT_CONFIG'].get('user', 'name'),
            cfg['GIT_CONFIG'].get('user', 'email'),
        )


@cli.command()
@click.option('--no-sign', '-S', 'sign', default=True, is_flag=True,
              help='Turn off code signing.')
@click.option('--tag', '-t',
              help='Tag to publish. Default is the latest tag created.')
def publish():
    pass
