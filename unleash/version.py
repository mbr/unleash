import re


def replace_assign(data, varname, new_value):
    ASSIGN_RE = re.compile(BASE_ASSIGN_PATTERN % varname)

    def repl(m):
        return m.group(1) + new_value + m.group(3)

    return ASSIGN_RE.sub(repl, data)
