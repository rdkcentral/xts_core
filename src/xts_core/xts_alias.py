"""
Alias management for XTS.

Commands:
  xts --alias --list
  xts --alias <path|url|dir> [--name <name>]
  xts --alias --add <path|url|dir> [--name <name>]

Behavior:
- If a URL is provided:
    - download the .xts file
    - cache it under ~/.xts/cache/<filename>.xts
    - add an alias pointing to the cached local file
    - default alias name is filename without '.xts'
- If a file is provided:
    - cache it under ~/.xts/cache/<filename>.<hash>.xts
    - add an alias pointing to that file
    - default alias name is filename without '.xts'
- If a directory is provided:
    - add aliases for every '*.xts' file inside it
    - default alias name prefix is the directory name
    - if --name is provided, it becomes the prefix instead
    - aliases are created as '<prefix>/<filename_without_xts>'

Remove:
- `xts --alias --remove <name>` removes the alias mapping from aliases.json
"""

import os
import hashlib
import shutil
import json
import requests
from pathlib import Path
from urllib.parse import urlparse

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

# move these to utils
def _is_url(s: str) -> bool:
    """
    Return True if the string looks like an http(s) URL.
    """
    try:
        u = urlparse(s)
        return u.scheme in ("http", "https") and bool(u.netloc)
    except Exception:
        return False


def _strip_xts_suffix(name: str) -> str:
    """
    Remove a trailing '.xts' suffix from a filename.
    """
    return name[:-4] if name.endswith(".xts") else name


def _default_name_from_url(url: str) -> str:
    """
    Default alias name for a URL is the URL filename without '.xts'.
    """
    filename = Path(urlparse(url).path).name
    return _strip_xts_suffix(filename)


def _default_name_from_file(path: Path) -> str:
    """
    Default alias name for a file is the filename without '.xts'.
    """
    return _strip_xts_suffix(path.name)

def _cache_name_for_local_file(src: Path) -> str:
    """
    Produce a stable cache filename for a local file, avoiding collisoins
    between same-basename files in different directories.
    """
    resolved = str(src.expanduser().resolve())
    h = hashlib.sha256(resolved.encode("utf-8")).hexdigest()[:10]

    # Keep readability: original basename + short hash + .xts
    if src.name.endswith(".xts"):
        base = src.name[:-4]
        return f"{base}.{h}.xts"
    return f"{src.name}.{h}.xts"

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
    # filename = hashlib.sha256(url.encode()).hexdigest() + ".xts"
    filename = Path(urlparse(url).path).name
    if not filename:
        raise ValueError(f"URL does not contain a filename: {url}")
    
    cached_path = os.path.join(CACHE_DIR, filename)
    
    print(f"Fetching remote .xts config from: {url}")
    r = requests.get(url)
    r.raise_for_status()
    
    with open(cached_path, "w", encoding="utf-8") as f:
        f.write(r.text)

    return cached_path

def cache_local_file_to_cache(src: Path) -> str:
    """
    Copy a local .xts file into the cache and return the cached path.

    This refreshes (overwrites) the cached file whenever called.
    """
    ensure_dirs()

    src = src.expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Local file not found: {src}")

    cache_name = _cache_name_for_local_file(src)
    dst = Path(CACHE_DIR) / cache_name

    shutil.copy2(src, dst)  #ovewrite to refresh
    return str(dst)

def load_aliases() -> dict:
    """
    Load aliases from ~/.xts/aliases.json.

    Returns:
        dict: {alias_name: xts_path}
    """
    ensure_dirs()
    if not os.path.exists(ALIAS_FILE):
        return {}
    with open(ALIAS_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_aliases(aliases: dict) -> None:
    """
    Save aliases to ~/.xts/aliases.json.
    """
    ensure_dirs()
    with open(ALIAS_FILE, "w", encoding="utf-8") as f:
        json.dump(aliases, f, indent=2, sort_keys=True)

def add_alias(name: str, value: str) -> None:
    """
    Add or update an alias mapping.

    Args:
        name (str): Alias name.
        value (str): Local .xts path the alias points to.
    """
    aliases = load_aliases()
    aliases[name] = value
    save_aliases(aliases)


def list_aliases() -> dict:
    """
    Return the alias mapping dictionary.
    """
    return load_aliases()


def remove_alias(name: str) -> None:
    """
    Remove an alias if it exists.
    """
    aliases = load_aliases()
    if name in aliases:
        del aliases[name]
        save_aliases(aliases)


def resolve_alias_to_xts_path(alias_name: str) -> str | None:
    """
    Resolve an alias name to a local .xts file path.

    Args:
        alias_name (str): Alias name to resolve.

    Returns:
        str | None: Local path if found, else None.
    """
    aliases = load_aliases()
    return aliases.get(alias_name)


def add_alias_from_input(input_value: str, name: str | None) -> list[tuple[str, str]]:
    """
    Add alias(es) from a URL, file path, or directory.

    Returns:
        list[tuple[str, str]]: List of (alias_name, resolved_path) entries added.
    """
    added: list[tuple[str, str]] = []

    # URL case
    if _is_url(input_value):
        cached = fetch_url_to_cache(input_value)
        alias_name = name or _default_name_from_url(input_value)
        add_alias(alias_name, cached)
        added.append((alias_name, cached))
        return added

    p = Path(input_value).expanduser()

    # File case
    if p.is_file():
        alias_name = name or _default_name_from_file(p)
        cached = cache_local_file_to_cache(p)
        add_alias(alias_name, cached)
        added.append((alias_name, cached))
        return added

    # Directory case
    if p.is_dir():
        xts_files = sorted(p.glob("*.xts"))
        if not xts_files:
            raise FileNotFoundError(f"No .xts files found in directory: {p}")

        prefix = name or p.name

        for f in xts_files:
            base = _default_name_from_file(f)
            alias_name = f"{prefix}/{base}"
            cached = cache_local_file_to_cache(f)
            add_alias(alias_name, cached)
            added.append((alias_name, cached))

        return added

    raise FileNotFoundError(f"Not a url, file, or directory: {input_value}")

def _print_alias_help_and_list() -> None:
    print("Usage:")
    print("  xts --alias --list")
    print("  xts --alias --help")
    print("  xts --alias --remove <name>")
    print("  xts --alias <path|url|dir> [--name <name>]")
    print("  xts --alias --add <path|url|dir> [--name <name>]")
    print("\nCurrent aliases:")
    aliases = list_aliases()
    if not aliases:
        print("  (none)")
    else:
        for k, v in sorted(aliases.items()):
            print(f"  {k} -> {v}")

def run_alias_builtin(argv: list[str]) -> int:
    """
    Built-in alias CLI.

    Supported:
      xts --alias --list
      xts --alias --help
      xts --alias --remove <name>
      xts --alias <path|url|dir> [--name <name>]
      xts --alias --add <path|url|dir> [--name <name>]

    Notes:
    - If <path|url|dir> is provided, adding is the default behavior.
    - For directories, all *.xts files are added.
    """

    input_value = None
    name = None
    do_list = False
    remove_name = None
    do_help = False

    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok == "--list":
            do_list = True
            i += 1
            continue
        if tok == "--remove":
            if i + 1 >= len(argv):
                print("ERROR: --remove requires an alias name")
                return 2
            remove_name = argv[i + 1]
            i += 2
            continue
        if tok == "--add":
            # optional; doesn't change behavior
            i += 1
            continue
        if tok == "--name":
            if i + 1 >= len(argv):
                print("ERROR: --name requires a value")
                return 2
            name = argv[i + 1]
            i += 2
            continue
        if tok in ("--help", "-h"):
            do_help = True
            i += 1
            continue

        # first non-flag token is input_value
        if input_value is None:
            input_value = tok
            i += 1
            continue

        # unexpected extra tokens
        print(f"ERROR: Unexpected argument: {tok}")
        return 2

    if remove_name is not None:
        removed = remove_alias(remove_name)
        if removed:
            print(f"Removed alias: {remove_name}")
            return 0
        print(f"Alias not found: {remove_name}")
        return 2
    
    if do_list:
        aliases = list_aliases()
        if not aliases:
            print("  (none)")
        for k, v in sorted(aliases.items()):
            print(f"{k} -> {v}")
        return 0

    if input_value:
        added = add_alias_from_input(input_value, name)
        for k, v in added:
            print(f"{k} -> {v}")
        return 0
    
    if do_help:
        _print_alias_help_and_list()
        return 0


    print("Usage:")
    print("  xts --alias --list")
    print("  xts --alias --help")
    print("  xts --alias --remove <name>")
    print("  xts --alias <path|url|dir> [--name <name>]")
    print("  xts --alias --add <path|url|dir> [--name <name>]")
    return 2
