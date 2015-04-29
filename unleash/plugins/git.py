import subprocess

from click import Option
from shutilwhich import which


PLUGIN_NAME = 'git'


def setup(cli):
    cli.params.append(Option(
        ['--git-binary'], default='git',
        help='Path to git binary to use.'
    ))
    cli.commands['publish'].params.append(Option(
        ['--git-remote'], default='origin',
        help='Remote to push release tags to (default: origin).',
    ))


def collect_info(ctx):
    info = ctx['info']

    gb = ctx['opts']['git_binary']
    git_binary = which(gb)
    if not git_binary:
        ctx['issues'].error('Could not find git binary: {}.'.format(gb))

    info['git_path'] = git_binary

    ref = ctx['ref']

    info['git_tag_name'] = ref.tag_name


def publish_release(ctx):
    info = ctx['info']
    tag = info['git_tag_name']
    remote = ctx['opts']['git_remote']
    issues = ctx['issues']

    if not tag:
        ctx['issues'].warn('Published release is not from a tag',
                           'The release you are publishing was not retrieved '
                           'from a tag. For safety reasons, it will not get '
                           'pushed upstream.')
    else:
        if not ctx['opts']['dry_run']:
            ctx['log'].info('Pushing tag \'{}\' to remote \'{}\''.format(
                tag, remote
            ))
            try:
                args = [ctx['opts']['git_binary'],
                        'push',
                        remote,
                        tag]
                subprocess.check_output(args, cwd=ctx['opts']['root'])
            except subprocess.CalledProcessError as e:
                issues.error('Failed to push tag:\n{}'.format(e.output))

        else:
            ctx['log'].info('Not pushing tag \'{}\' to remote \'{}\''
                            ' (dry-run)'.format(tag, remote))
