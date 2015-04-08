#!/usr/bin/env python

import ast

VERSION_STRING_ID = '__version__'


class VersionVisitor(ast.NodeVisitor):
    version_node = None

    def visit_Module(self, node):
        for n in node.body:
            self.visit(n)

    def visit_FunctionDef(self, node):
        pass  # ignore

    def visit_ClassDef(self, node):
        pass  # ignore

    def visit_Assign(self, node):
        if len(node.targets) == 1 and node.targets[0].id == VERSION_STRING_ID:
            if not hasattr(node.value, 's'):
                raise ValueError('Version must be string (in line %d).' %
                                 node.lineno)
            if self.version_node:
                raise ValueError('Duplicate version strings: %r in line %d '
                                 'and %r in line %d.' % (
                                     self.version_node.value.s,
                                     self.version_node.lineno,
                                     node.value.s,
                                     node.lineno)
                                 )

            self.version_node = node


def extract_version(filename):
    with open(filename) as f:
        buf = f.read()
        module = ast.parse(buf, filename)

    v = VersionVisitor()
    v.visit(module)

    print 'version', v.version_node.value.s

    lineno = 0
    pos = 0

    while pos < len(buf):
        if lineno == v.version_node.lineno-1:
            print "FOUND", buf[pos:]
            for i in xrange(v.version_node.col_offset):
                pos += 1

            # skip __version__
            pos += len(VERSION_STRING_ID)

            # skip whitespace and '=' operator
            while buf[pos].isspace() or buf[pos] == '=':
                print 'skip', buf[pos]
                pos += 1

            print 'at pos', pos
            print buf[pos:]

        if buf[pos] == '\n':
            lineno += 1
        pos += 1

    return v.version_node.lineno, v.version_node.col_offset


if __name__ == '__main__':
    print extract_version('extraction_target.py')
