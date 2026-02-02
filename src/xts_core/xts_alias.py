"""
Alias management for XTS.

Commands:
  xts --alias --list
  xts --alias <path|url|dir> [--name <name>]
  xts --alias --add <path|url|dir> [--name <name>]
  xts --alias --remove <name>
  xts --alias --refresh <name>

Behavior:
- If a URL is provided:
    - download the .xts file
    - cache it under ~/.xts/cache/<filename>.xts
    - add an alias pointing to the cached local file
    - store the original URL for future refreshes
    - default alias name is filename without '.xts'
- If a file is provided:
    - cache it under ~/.xts/cache/<filename>.<hash>.xts
    - add an alias pointing to that file
    - store the original file path for future refreshes
    - default alias name is filename without '.xts'
- If a directory is provided:
    - add aliases for every '*.xts' file inside it
    - default alias name prefix is the directory name
    - if --name is provided, it becomes the prefix instead
    - aliases are created as '<prefix>/<filename_without_xts>'

Remove:
- `xts --alias --remove <name>` removes the alias mapping from aliases.json

Refresh:
- `xts --alias --refresh <name>` re-downloads or re-copies the file from its original source
"""

import argparse
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

try:
    from .xts_arg_parser import XTSArgumentParser
except:
    from xts_core.xts_arg_parser import XTSArgumentParser

CACHE_DIR = os.path.expanduser("~/.xts/cache")
ALIAS_FILE = os.path.expanduser("~/.xts/aliases.json")

def _get_cached_path(alias_info) -> str:
    """
    Extract cached path from alias info, handling both old and new formats.
    
    Args:
        alias_info: Either a string (old format) or dict with 'cached_path' key (new format)
    
    Returns:
        The cached file path
    """
    if isinstance(alias_info, dict):
        return alias_info.get("cached_path", "")
    return alias_info  # old format: just a string path


def _get_source(alias_info) -> str:
    """
    Extract source path from alias info, handling both old and new formats.
    
    Args:
        alias_info: Either a string (old format) or dict with 'source' key (new format)
    
    Returns:
        The source path/URL
    """
    if isinstance(alias_info, dict):
        return alias_info.get("source", alias_info.get("cached_path", "unknown"))
    return alias_info  # old format: just a string path


def ensure_dirs():
    """Ensure that the cache and alias directories exist.

    Creates the cache directory (`CACHE_DIR`) and the directory
    containing the alias file (`ALIAS_FILE`) if they do not already exist.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(ALIAS_FILE), exist_ok=True)

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
    Produce a stable cache filename for a local file, avoiding collisions
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

    shutil.copy2(src, dst)  # overwrite to refresh
    return str(dst)

def load_aliases() -> dict:
    """
    Load aliases from ~/.xts/aliases.json.

    Returns:
        dict: {alias_name: {"cached_path": str, "source": str}}
              For backwards compatibility, old format {alias_name: path_string}
              is automatically migrated to new format.
    """
    ensure_dirs()
    if not os.path.exists(ALIAS_FILE):
        return {}
    with open(ALIAS_FILE, encoding="utf-8") as f:
        aliases = json.load(f)
    
    # Migrate old format to new format
    needs_migration = False
    for name, value in list(aliases.items()):
        if isinstance(value, str):
            # Old format: migrate to new format
            # For migrated aliases, source is same as cached_path (unknown original)
            aliases[name] = {
                "cached_path": value,
                "source": value
            }
            needs_migration = True
    
    if needs_migration:
        save_aliases(aliases)
    
    return aliases


def save_aliases(aliases: dict) -> None:
    """
    Save aliases to ~/.xts/aliases.json.
    """
    ensure_dirs()
    with open(ALIAS_FILE, "w", encoding="utf-8") as f:
        json.dump(aliases, f, indent=2, sort_keys=True)

def add_alias(name: str, cached_path: str, source: str) -> None:
    """
    Add or update an alias mapping.

    Args:
        name (str): Alias name.
        cached_path (str): Local cached .xts path the alias points to.
        source (str): Original source (URL or file path) of the alias.
    """
    aliases = load_aliases()
    aliases[name] = {
        "cached_path": cached_path,
        "source": source
    }
    save_aliases(aliases)


def list_aliases() -> None:
    aliases = load_aliases()
    if not aliases:
        utils.warning('No aliases added')
    for k, v in sorted(aliases.items()):
        source = _get_source(v)
        utils.info(f"[bold]{k}[/bold] [default]->[/default] {source}")


def remove_alias(name: str) -> bool:
    """
    Remove an alias if it exists.
    """
    aliases = load_aliases()

    if name not in aliases:
        return False
    
    alias_info = aliases[name]
    cached_path = _get_cached_path(alias_info)
    del aliases[name] 
    save_aliases(aliases)
    
    # remove cached file if it's inside ~/.xts/cache
    try:
        cache_root = Path(CACHE_DIR).expanduser().resolve()
        target = Path(cached_path).expanduser().resolve()
        if cache_root in target.parents and target.is_file():
            target.unlink()
    except Exception:
        # don't fail alias removal due to cache cleanup issues
        pass

    return True 


def resolve_alias_to_xts_path(alias_name: str) -> str | None:
    """
    Resolve an alias name to a local .xts file path.

    Args:
        alias_name (str): Alias name to resolve.

    Returns:
        str | None: Local path if found, else None.
    """
    aliases = load_aliases()
    alias_info = aliases.get(alias_name)
    if alias_info is None:
        return None
    return _get_cached_path(alias_info)


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
        add_alias(alias_name, cached, input_value)  # source is the URL
        added.append((alias_name, cached))
        return added

    p = Path(input_value).expanduser()

    # File case
    if p.is_file():
        alias_name = name or _default_name_from_file(p)
        cached = cache_local_file_to_cache(p)
        source = str(p.resolve())  # source is the resolved file path
        add_alias(alias_name, cached, source)
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
            source = str(f.resolve())  # source is the resolved file path
            add_alias(alias_name, cached, source)
            added.append((alias_name, cached))

        return added

    raise FileNotFoundError(f"Not a url, file, or directory: {input_value}")


def refresh_alias(alias_name: str) -> tuple[str, str]:
    """
    Refresh an alias by re-fetching or re-copying from the original source.

    Args:
        alias_name (str): Name of the alias to refresh.

    Returns:
        tuple[str, str]: (alias_name, new_cached_path)

    Raises:
        ValueError: If the alias doesn't exist or was migrated from old format.
        FileNotFoundError: If the source file/directory no longer exists.
    """
    aliases = load_aliases()
    
    if alias_name not in aliases:
        raise ValueError(f"Alias not found: {alias_name}")
    
    alias_info = aliases[alias_name]
    if not isinstance(alias_info, dict):
        raise ValueError(f"Cannot refresh alias '{alias_name}': missing source information")
    
    source = alias_info.get("source")
    cached = alias_info.get("cached_path")
    
    if not source:
        raise ValueError(f"Cannot refresh alias '{alias_name}': no source information available")
    
    # Check if this is a migrated alias (source == cached_path means unknown original)
    if source == cached:
        raise ValueError(
            f"Cannot refresh alias '{alias_name}': original source unknown (migrated from old format). "
            f"Remove and re-add the alias to enable refresh."
        )
    
    # Determine if source is a URL or local path
    if _is_url(source):
        # Re-fetch from URL
        cached = fetch_url_to_cache(source)
        add_alias(alias_name, cached, source)
        return (alias_name, cached)
    else:
        # Re-copy from local file
        p = Path(source).expanduser()
        if not p.is_file():
            raise FileNotFoundError(f"Source file not found: {source}")
        cached = cache_local_file_to_cache(p)
        add_alias(alias_name, cached, source)
        return (alias_name, cached)


def run_alias_builtin(argv: list[str]) -> int:
    """
    Built-in alias CLI.

    Supported:
      xts --alias --list
      xts --alias --help
      xts --alias --remove <name>
      xts --alias --refresh <name>
      xts --alias --add <path|url|dir> [--name <name>]

    Notes:
    - For directories, all *.xts files are added.
    """
    alias_parser = XTSArgumentParser(prog='xts --alias', add_help=True)
    alias_parser.add_argument('uri',
                              action='store',
                              default=None,
                              help='URI of xts file to add or alias name',
                              nargs='?')
    alias_parser.add_argument('--list',
                              action='store_true',
                              default=False,
                              help='List all aliases')
    alias_parser.add_argument('--remove', '--rm',
                              action='store',
                              help='Remove alias',
                              default=None,
                              metavar='ALIAS_NAME',
                              dest='remove')
    alias_parser.add_argument('--refresh',
                              action='store',
                              help='Refresh alias from original source',
                              default=None,
                              metavar='ALIAS_NAME',
                              dest='refresh')
    alias_parser.add_argument('--add',
                              action='store',
                              metavar='URI',
                              default=None,
                              help='Add an alias of an xts file URI')
    alias_parser.add_argument('--name',
                              action='store',
                              help='Name to use for alias')
    # show help & current aliases if no args
    if not argv:
        alias_parser.print_help()
        print("\nCurrent aliases:")
        list_aliases()
        return 0
    
    args = alias_parser.parse_args(argv)
    
    if args.list:
        list_aliases()
        return 0
    
    if args.remove is not None:
        if remove_alias(args.remove):
            print(f"Removed alias: {args.remove}")
            return 0
        print(f"Alias not found: {args.remove}")
        return 2

    if args.refresh is not None:
        try:
            name, cached_path = refresh_alias(args.refresh)
            print(f"Refreshed alias: {name} -> {cached_path}")
            return 0
        except (ValueError, FileNotFoundError) as e:
            utils.error(str(e))
            return 2
        except Exception as e:
            utils.error(f"Failed to refresh alias: {str(e)}")
            return 2

    if args.uri and args.add:
        alias_parser.error('Provide the URI only once (either positional OR via "--add").')
        return 2

    input_value = args.add or args.uri
    if not input_value:
        alias_parser.print_help()
        return 2

    try:
        added = add_alias_from_input(input_value, args.name)
    except (FileNotFoundError, ValueError) as e:
        alias_parser.error(str(e))
        return 2
    except Exception as e:
        utils.error(f"Failed to add alias: {str(e)}")
        return 2
    
    for k, v in added:
        print(f"{k} -> {v}")
    return 0
