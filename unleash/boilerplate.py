import json
import os

import click
from jinja2 import Environment, FileSystemLoader
from pluginbase import PluginBase


plugin_base = PluginBase(package='unleash.boilerplate_plugins')


class Choice(object):
    def __init__(self, choices):
        self.choices = set(choices)

    def __call__(self, val):
        if val not in self.choices:
            raise ValueError('Must be one of {}'.format(
                ', '.join(self.choices)
            ))

        return val


class Variable(object):
    def __init__(self, d):
        self.name = d['var']
        self.user_value = None
        self.required = True

        vartype = d.get('type')

        if vartype == 'choice':
            self.type = Choice(d['choices'])
        elif vartype == 'int':
            self.type = int
        elif vartype == 'float':
            self.type = float
        else:
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


class RunContext(object):
    def __init__(self, recipe_dir, dest, vars={}):
        self.recipe_dir = recipe_dir
        self.dest = dest
        self.vars = vars

        # prepare jinja env
        self.env = Environment(loader=FileSystemLoader(
            os.path.join(self.recipe_dir, 'templates'),
        ))
        self.env.globals['vars'] = self.vars

    def render_template_to(self, template, _target=None, **kwargs):
        tpl = self.env.get_template(template)
        buf = tpl.render(**kwargs)

        _target = _target or template
        outfn = os.path.join(self.dest, _target)
        with open(outfn, 'w') as out:
            out.write(buf)

        click.secho('wrote {}'.format(outfn), fg='green', bold=True)


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

    def enter_var(self, var):
        while True:
            nval = click.prompt('Enter new value for {}'.format(var.name))

            try:
                var.set_value(nval)
            except (ValueError, TypeError) as e:
                click.echo('Invalid value: {}'.format(e))
            else:
                break

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

            val = click.prompt('Select option [#/q/a/y]')
            click.echo()

            if val == 'q':
                return False

            if val == 'y':
                for var in self.vars:
                    if not var.is_valid():
                        click.echo(
                            '{} does not have a valid value'.format(var.name)
                        )
                        break
                else:
                    return True
                continue

            if val == 'a':
                # ask for each missing value
                for var in self.vars:
                    if not var.is_valid():
                        self.enter_var(var)

                continue

            try:
                val = int(val)
                if val >= len(self.vars):
                    raise ValueError('Invalid selection')
            except ValueError as e:
                click.echo(str(e))
                click.echo()
                continue

            var = self.vars[val]

            self.enter_var(var)

    def run(self, destdir):
        # import the module
        src = plugin_base.make_plugin_source(
            searchpath=[self.path]
        )

        with src:
            from unleash.boilerplate_plugins import recipe

        vars = {v.name.lower().replace(' ', '_'): v.get_value()
                for v in self.vars}
        ctx = RunContext(self.path, destdir, vars)
        recipe.run(ctx)
