import os
import hashlib
import json
import requests
import glob

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

def find_xts_files(path, recursive=False):
    """Find all .xts files in a directory.

    Args:
        path: Directory path to search in (can be relative or absolute).
        recursive: If True, search recursively in subdirectories.

    Returns:
        List of absolute paths to .xts files found.
    """
    path = os.path.abspath(path)
    
    if not os.path.isdir(path):
        return []
    
    xts_files = []
    if recursive:
        # Recursive search
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith('.xts'):
                    xts_files.append(os.path.join(root, file))
    else:
        # Non-recursive search - only immediate directory
        for file in os.listdir(path):
            file_path = os.path.join(path, file)
            if os.path.isfile(file_path) and file.endswith('.xts'):
                xts_files.append(file_path)
    
    return sorted(xts_files)

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

