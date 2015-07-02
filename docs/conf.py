# -*- coding: utf-8 -*-

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']
source_suffix = '.rst'
master_doc = 'index'

project = u'unleash'
copyright = u'2015, Marc Brinkmann'

version = '0.7.2'
release = '0.7.2.dev1'

exclude_patterns = ['_build']
pygments_style = 'sphinx'
html_theme = 'alabaster'

intersphinx_mapping = {'http://docs.python.org/': None}
