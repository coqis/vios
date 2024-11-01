# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

apidoc_module_dir = '_module'
apidoc_output_dir = 'api'
# apidoc_excluded_paths = ['tests']
apidoc_separate_modules = True


# -- Project information -----------------------------------------------------

project = 'SystemQ'
copyright = '2022, BAQIS'
author = 'BAQIS'

# The full version, including alpha/beta/rc tags
release = '1.0'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    # 'sphinxcontrib.napoleon',
    # 'sphinxcontrib.apidoc',
    'autoapi.extension',
    'sphinx.ext.viewcode',
    'sphinx_togglebutton',
    # 'recommonmark',
    'myst_parser',
    'sphinx.ext.mathjax',
    'sphinx_math_dollar'
]

autoapi_dirs = ['./_module']

myst_enable_extensions = [
    "amsmath",
    "attrs_inline",
    "colon_fence",
    "deflist",
    "dollarmath",
    "fieldlist",
    "html_admonition",
    "html_image",
    "linkify",
    "replacements",
    "smartquotes",
    "strikethrough",
    "substitution",
    "tasklist",
]

mathjax3_config = {
#   "tex": {
#     "inlineMath": [['\\(', '\\)']],
#     "displayMath": [["\\[", "\\]"]],
#   },
  'tex2jax': {
      'inlineMath': [['$$','$$'],['$$','$$']],
      'displayMath': [['$','$'],['$$','$$']],
    }
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
source_parsers = {
    '.md': 'recommonmark.parser.CommonMarkParser',
}
exclude_patterns = []
source_suffix = ['.rst', '.md'] 


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.

html_theme = "sphinxawesome_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
html_logo = "_static/dock.png"
