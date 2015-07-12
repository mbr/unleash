import json
import os

import click


class Variable(object):
    def __init__(self, d):
        self.name = d['var']
        self.user_value = None
        self.required = True
        self.type = str
        self.default = self.type(d['default']) if 'default' in d else None

    @classmethod
    def from_dict(self, d):
        return Variable(d)

    def is_valid(self):
        if not self.required:
            return True

        return (self.user_value or self.default) is not None

    def format_value(self):
        fmt = {}

        if self.user_value is not None:
            fmt = {'fg': 'green', 'bold': True}

        elif self.default is not None:
            fmt = {'fg': 'white'}

        return click.style(str(self.get_value()), **fmt)

    def get_value(self):
        if self.user_value:
            return self.user_value

        if self.default is not None:
            return self.default

        return None

    def set_value(self, new_value):
        self.user_value = self.type(new_value)
        return True


class Recipe(object):
    def __init__(self, name):
        tpl_dir = os.path.join(click.get_app_dir('unleash'), 'recipes')

        # search for recipe
        path = os.path.join(tpl_dir, name)
        if os.path.exists(path):
            self.path = path
        else:
            suggestion = os.path.join(tpl_dir, name)
            raise OSError('Could not find recipe "{}". Does {} exist?'
                          .format(name, suggestion))

        self.name = name

        # load questions
        self.vars = [
            Variable.from_dict(d) for d in
            json.load(open(os.path.join(self.path, 'variables.json')))
        ]

        self.answers = {}

    def collect_answers(self):
        if not self.vars:
            return

        # prepare templates
        max_var_len = max(len(v.name) for v in self.vars)
        TPL = '[{:-2d}] {:' + str(max_var_len) + '} : {}'

        while True:
            # show the menu
            for n, var in enumerate(self.vars):
                name_fmt = {}
                if not var.is_valid():
                    name_fmt['fg'] = 'red'

                click.echo(TPL.format(
                    n,
                    click.style(var.name, **name_fmt),
                    var.format_value(),
                ))

            val = click.prompt('Select option [#/q/y]')
            click.echo()

            if val == 'q':
                return False

            if val == 'y':
                # FIXME: validate
                return True

            try:
                val = int(val)
                if val >= len(self.vars):
                    raise ValueError('Invalid selection')
            except ValueError as e:
                click.echo(str(e))
                click.echo()
                continue

            var = self.vars[val]

            # enter new value
            while True:
                nval = click.prompt('Enter new value for {}'.format(var.name))

                try:
                    var.set_value(nval)
                except (ValueError, TypeError) as e:
                    click.echo('Invalid value')
                else:
                    break
