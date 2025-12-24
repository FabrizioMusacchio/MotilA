# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys
from datetime import datetime
sys.path.insert(0, os.path.abspath("../.."))  # ../.. = where motila/ is located

from importlib.metadata import version as pkg_version, PackageNotFoundError, packages_distributions

def _resolve_omio_version() -> str:
    # primary: known PyPI distribution name
    try:
        return pkg_version("omio-microscopy")
    except PackageNotFoundError:
        pass

    # fallback: map import package -> installed distribution(s)
    try:
        dist_names = packages_distributions().get("omio", [])
        for dist in dist_names:
            try:
                return pkg_version(dist)
            except PackageNotFoundError:
                continue
    except Exception:
        pass

    return "0.0.0+unknown"

project = 'MotilA'
copyright = '2025, Fabrizio Musacchio'
author = 'Fabrizio Musacchio'
release = _resolve_omio_version()
copyright = f"{datetime.now().year}, {author}"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
    "sphinx.ext.mathjax",
]
autosummary_generate = True
napoleon_google_docstring = False
napoleon_numpy_docstring = True

html_theme = "sphinx_rtd_theme"

templates_path = ['_templates']
exclude_patterns = []

# define mathjax_path to use a specific version from CDN:
mathjax_path = "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"

mathjax3_config = {
    "tex": {
        # enable $...$ and $$...$$ in addition to \(..\), \[..\]
        "inlineMath": [["$", "$"], ["\\(", "\\)"]],
        "displayMath": [["$$", "$$"], ["\\[", "\\]"]],
    }
}


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_static_path = ['_static']
