import os
import hashlib
import json
import requests

try:
    from . import utils
except:
    from xts_core import utils

CACHE_DIR = os.path.expanduser("~/.xts/cache")
ALIAS_FILE = os.path.expanduser("~/.xts/aliases.json")

def ensure_dirs():
    """Ensure that the cache and alias directories exist.

    Creates the cache directory (`CACHE_DIR`) and the directory
    containing the alias file (`ALIAS_FILE`) if they do not already exist.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(ALIAS_FILE), exist_ok=True)

def fetch_url_to_cache(url):
    """Fetch a remote .xts file and store it in the cache.

    If the URL has been cached before, returns the existing cached file path.
    Otherwise, fetches the content from the URL, stores it in the cache,
    and then returns the cached path.

    Args:
        url: The remote URL pointing to a .xts file.

    Returns:
        The filesystem path to the cached .xts file.
    """
    ensure_dirs()
    filename = hashlib.sha256(url.encode()).hexdigest() + ".xts"
    path = os.path.join(CACHE_DIR, filename)

    if not os.path.exists(path):
        print(f"Fetching remote .xts config from: {url}")
        r = requests.get(url)
        r.raise_for_status()
        with open(path, "w", encoding="utf-8") as f:
            f.write(r.text)

    return path

def resolve_alias_or_url(arg):
    """Resolve an alias or URL to a filesystem path.

    - If the argument matches an alias, resolve it to its target.
    - If the argument is a URL, fetch and cache it.
    - Otherwise, return the argument unchanged.

    Args:
        arg: Alias name, URL, or local path.

    Returns:
        The resolved filesystem path (or unchanged argument if not resolvable).
    """
    ensure_dirs()
    aliases = {}
    if os.path.exists(ALIAS_FILE):
        with open(ALIAS_FILE) as f:
            aliases = json.load(f)

    if arg in aliases:
        arg = aliases[arg]

    if utils.is_url(arg):
        return fetch_url_to_cache(arg)

    return arg

def add_alias(name, value):
    """Add or update an alias.

    Args:
        name: Alias name to add or update.
        value: The value (path or URL) the alias should point to.
    """
    ensure_dirs()
    aliases = {}
    if os.path.exists(ALIAS_FILE):
        with open(ALIAS_FILE) as f:
            aliases = json.load(f)
    aliases[name] = value
    with open(ALIAS_FILE, "w") as f:
        json.dump(aliases, f, indent=2)

def list_aliases():
    """List all defined aliases.

    Returns:
        A dictionary mapping alias names to their values.
    """
    if not os.path.exists(ALIAS_FILE):
        return {}
    with open(ALIAS_FILE) as f:
        return json.load(f)

def remove_alias(name):
    """Remove an alias if it exists.

    Args:
        name: Alias name to remove.
    """
    if not os.path.exists(ALIAS_FILE):
        return
    with open(ALIAS_FILE) as f:
        aliases = json.load(f)
    if name in aliases:
        del aliases[name]
    with open(ALIAS_FILE, "w") as f:
        json.dump(aliases, f, indent=2)

