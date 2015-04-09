from logbook import Logger

log = Logger('unleash')


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


class IssueCollector(object):
    def __init__(self):
        self.issues = []
        self.log = log

    def report(self, *args, **kwargs):
        issue = Issue(*args, **kwargs)
        self.issues.append(issue)

        getattr(log, issue.severity)(issue.format_issue())

        if issue.suggestion:
            log.info(issue.format_suggestion())
