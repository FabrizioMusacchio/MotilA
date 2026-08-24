"""
Small top-level convenience helpers for MotilA.

author: Fabrizio Musacchio  
date: September 2023
ported to modular MotilA: August 2026
"""
# %% IMPORTS
from importlib.metadata import PackageNotFoundError, version

# %% HELLO WORLD

def get_motila_version():
    """
    Return the installed MotilA package version.
    """
    try:
        return version("motila")
    except PackageNotFoundError:
        return "unknown"


def hello_world():
    """
    Prints a friendly message to the user.
    """
    print(f"Hello, World! Welcome to MotilA. You are using version {get_motila_version()}.")

# %% END
