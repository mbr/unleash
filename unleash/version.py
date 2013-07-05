import re
import verlib


class NormalizedVersion(verlib.NormalizedVersion):
    def increment(self):
        main = list(self.parts[0])
        main[-1] += 1
        self.parts = (tuple(main), verlib.FINAL_MARKER, verlib.FINAL_MARKER)

    def set_dev_version(self, num=1):
        self.parts = (self.parts[0], verlib.FINAL_MARKER, ('dev%d' % num,))

    def drop_extras(self):
        main, prerel, postdev = self.parts
        self.parts = (main, verlib.FINAL_MARKER, verlib.FINAL_MARKER)

    def copy(self):
        return self.__class__(str(self))

    @classmethod
    def suggest_from_string(cls, s):
        return cls(verlib.suggest_normalized_version(s))


_quotes = "['|\"|\"\"\"]"
BASE_VERSION_PATTERN = r'(%s=\s*[ubr]?' + _quotes + r')(.*?)(' + _quotes + r')'


def find_version(data, varname):
    VERSION_RE = re.compile(BASE_VERSION_PATTERN % varname)

    if len(VERSION_RE.findall(data)) != 1:
        raise ValueError('Found multiple %s-strings.' % varname)

    return NormalizedVersion.suggest_from_string(
        VERSION_RE.search(data).group(2)
    )


def replace_version(data, varname, new_version):
    VERSION_RE = re.compile(BASE_VERSION_PATTERN % varname)

    def repl(m):
        return m.group(1) + new_version + m.group(3)

    return VERSION_RE.sub(repl, data)
