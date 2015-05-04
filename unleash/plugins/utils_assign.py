from unleash.exc import PluginError

import re


# regular expression for finding assignments
_quotes = "['|\"|\"\"\"]"
BASE_ASSIGN_PATTERN = r'({}\s*=\s*[ubr]?' + _quotes + r')(.*?)(' +\
                      _quotes + r')'


def find_assign(data, varname):
    """Finds a substring that looks like an assignment.

    :param data: Source to search in.
    :param varname: Name of the variable for which an assignment should be
                    found.
    """
    ASSIGN_RE = re.compile(BASE_ASSIGN_PATTERN.format(varname))

    if len(ASSIGN_RE.findall(data)) > 1:
        raise PluginError('Found multiple {}-strings.'.format(varname))

    if len(ASSIGN_RE.findall(data)) < 1:
        raise PluginError('No version assignment ("{}") found.'
                          .format(varname))

    return ASSIGN_RE.search(data).group(2)


def replace_assign(data, varname, new_value):
    ASSIGN_RE = re.compile(BASE_ASSIGN_PATTERN.format(varname))

    def repl(m):
        return m.group(1) + new_value + m.group(3)

    return ASSIGN_RE.sub(repl, data)
