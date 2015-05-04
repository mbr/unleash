from .exc import PluginError


class Issue(object):
    # severities are:
    #   warning  - can be ignored and still release
    #   error    - prevents releasing, issue with source
    #   critical - unexpected error, might be out of our hands or program bug
    def __init__(self, channel, message, severity='warning', suggestion=None):
        assert severity in ('warning', 'error', 'critical')
        self.message = message
        self.severity = severity
        self.channel = channel
        self.suggestion = suggestion

    def format_issue(self):
        return u'[{}:{}] {}'.format(self.severity, self.channel, self.message)

    def format_suggestion(self):
        return u'[{}:{}] {}'.format(
            self.severity, self.channel, self.suggestion
        )

    def __str__(self):
        return u'<Issue {!r}>'.format(self.message)


class ChannelReporter(object):
    def __init__(self, collector, channel_name):
        self.collector = collector
        self.channel_name = channel_name

    def warn(self, message, suggestion=None):
        self.collector.report(self.channel_name,
                              message,
                              severity='warning',
                              suggestion=suggestion)

    def error(self, message, suggestion=None):
        self.collector.report(self.channel_name,
                              message,
                              severity='error',
                              suggestion=suggestion)
        raise PluginError('Plugin reported error.')

    def critical(self, message, suggestion=None):
        self.collector.report(self.channel_name,
                              message,
                              severity='critical',
                              suggestion=suggestion)
        raise PluginError('Plugin reported critical error')


class IssueCollector(object):
    def __init__(self, log=None):
        self.issues = []
        self.log = log

    def report(self, *args, **kwargs):
        issue = Issue(*args, **kwargs)
        self.issues.append(issue)

        if self.log:
            getattr(self.log, issue.severity)(issue.message)

    def channel(self, channel_name):
        return ChannelReporter(self, channel_name)
