# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Compliance Tool for Accelerator Management (CTAM)"
copyright = "2023, multiple"
author = "multiple"
release = "1.0"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.todo",
    "sphinx_autodoc_typehints",
    "sphinx_markdown_builder",
    "sphinxcontrib.mermaid",
    "autoapi.extension",
]

templates_path = ["_templates"]

exclude_patterns = []

autodoc_typehints = "signature"
autoapi_dirs = ["../../ctam"]
autoapi_type = "python"
autoapi_python_use_implicit_namespaces = False

autoapi_options = [
    "members",
    "undoc-members",
    "private-members",
    "show-module-summary",
    "imported-members",
    "show-inheritance",
]


todo_include_todos = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
