import subprocess

from click import Option
from shutilwhich import which
from unleash import opts, info, log, issues


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


def collect_info():
    gb = opts['git_binary']
    git_binary = which(gb)
    if not git_binary:
        issues.error('Could not find git binary: {}.'.format(gb))

    info['git_path'] = git_binary
    info['git_tag_name'] = info['ref'].tag_name


def publish_release():
    tag = info['git_tag_name']
    remote = opts['git_remote']

    if not tag:
        issues.warn('Published release is not from a tag. The release you are '
                    'publishing was not retrieved from a tag. For safety '
                    'reasons, it will not get pushed upstream.')
    else:
        if not opts['dry_run']:
            log.info('Pushing tag \'{}\' to remote \'{}\''.format(
                tag, remote
            ))
            try:
                args = [opts['git_binary'],
                        'push',
                        remote,
                        tag]
                subprocess.check_output(args, cwd=opts['root'])
            except subprocess.CalledProcessError as e:
                issues.error('Failed to push tag:\n{}'.format(e.output))

        else:
            log.info('Not pushing tag \'{}\' to remote \'{}\' (dry-run)'
                     .format(tag, remote))
