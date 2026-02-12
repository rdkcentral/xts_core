#!/usr/bin/env python3
#** *****************************************************************************
# *
# * If not stated otherwise in this file or this component's LICENSE file the
# * following copyright and licenses apply:
# *
# * Copyright 2026 RDK Management
# *
# * Licensed under the Apache License, Version 2.0 (the "License");
# * you may not use this file except in compliance with the License.
# * You may obtain a copy of the License at
# *
# *
# http://www.apache.org/licenses/LICENSE-2.0
# *
# * Unless required by applicable law or agreed to in writing, software
# * distributed under the License is distributed on an "AS IS" BASIS,
# * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# * See the License for the specific language governing permissions and
# * limitations under the License.
# *
#* ******************************************************************************

"""Enhanced XTS alias management with universal caching and update tracking.

Features:
- Universal caching (local AND remote files cached to ~/.xts/cache/)
- Directory scanning with recursive support
- Absolute path resolution
- Update detection for both local and remote files
- Graceful degradation when source files missing
- Broken alias detection and cleanup
"""

import os
import hashlib
import json
import time
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from . import utils
except:
    from xts_core import utils


CACHE_DIR = os.path.expanduser("~/.xts/cache")
ALIAS_FILE = os.path.expanduser("~/.xts/aliases.json")
METADATA_FILE = os.path.expanduser("~/.xts/metadata.json")
PROXIES_FILE = os.path.expanduser("~/.xts/proxies.json")


class AliasStatus:
    """Status indicators for aliases."""
    UP_TO_DATE = "✓"
    UPDATE_AVAILABLE = "↑"
    SOURCE_MISSING = "⚠"
    CACHED_ONLY = "📦"
    BROKEN = "✗"
    LOCAL = "L"
    REMOTE = "R"


def ensure_dirs():
    """Ensure that the cache and alias directories exist."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(ALIAS_FILE), exist_ok=True)


def compute_file_hash(filepath: str) -> str:
    """Compute SHA256 hash of file content."""
    sha256 = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception:
        return ""


def is_url(path: str) -> bool:
    """Check if path is a URL."""
    return path.startswith(('http://', 'https://'))


def get_cache_path(source: str, alias_name: str) -> str:
    """Get cache path for a source (URL or local file).
    
    Args:
        source: Source path or URL
        alias_name: Alias name (used for friendly cache filename)
        
    Returns:
        Absolute path to cached file
    """
    # Use alias name + hash of source for cache filename
    source_hash = hashlib.sha256(source.encode()).hexdigest()[:16]
    cache_filename = f"{alias_name}_{source_hash}.xts"
    return os.path.join(CACHE_DIR, cache_filename)


def find_xts_files(path: str, recursive: bool = False) -> List[str]:
    """Find all .xts files in a directory.
    
    Args:
        path: Directory path to search (can be relative or absolute)
        recursive: If True, search recursively
        
    Returns:
        List of absolute paths to .xts files found
    """
    path = os.path.abspath(os.path.expanduser(path))
    
    if not os.path.isdir(path):
        return []
    
    xts_files = []
    if recursive:
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith('.xts'):
                    xts_files.append(os.path.join(root, file))
    else:
        for file in os.listdir(path):
            file_path = os.path.join(path, file)
            if os.path.isfile(file_path) and file.endswith('.xts'):
                xts_files.append(file_path)
    
    return sorted(xts_files)


def fetch_remote_file(url: str, cache_path: str, proxy_config: Optional[Dict] = None) -> Tuple[bool, Optional[Dict]]:
    """Fetch remote .xts file and cache it.
    
    Args:
        url: Remote URL
        cache_path: Where to cache the file
        proxy_config: Optional proxy configuration dict with 'proxy', 'type', 'username', 'password'
        
    Returns:
        Tuple of (success, metadata_dict)
    """
    if not REQUESTS_AVAILABLE:
        utils.error("requests library not available - cannot fetch remote URLs")
        utils.info("Install with: pip install requests")
        return False, None
    
    try:
        # Setup proxy if configured
        proxies = None
        auth = None
        
        if proxy_config:
            proxy_url = proxy_config.get('proxy')
            proxy_type = proxy_config.get('type', 'http')
            username = proxy_config.get('username')
            password = proxy_config.get('password')
            
            if proxy_url:
                # Handle SSH proxy (not supported by requests directly)
                if proxy_type == 'ssh':
                    utils.warning("SSH proxy requires SSH tunnel setup (not implemented in fetch)")
                    utils.info("Set up SSH tunnel manually: ssh -D <port> <user>@<host>")
                    utils.info("Then use SOCKS5 proxy with localhost:<port>")
                    return False, None
                
                # If username/password provided, embed in proxy URL
                if username and password:
                    # Parse proxy to insert credentials
                    if '://' in proxy_url:
                        scheme, rest = proxy_url.split('://', 1)
                        proxy_url = f"{scheme}://{username}:{password}@{rest}"
                    else:
                        # Use proxy type to construct URL
                        if proxy_type == 'socks5':
                            proxy_url = f"socks5://{username}:{password}@{proxy_url}"
                        else:
                            proxy_url = f"{proxy_type}://{username}:{password}@{proxy_url}"
                elif not '://' in proxy_url:
                    # Add scheme if not present
                    if proxy_type == 'socks5':
                        proxy_url = f"socks5://{proxy_url}"
                    else:
                        proxy_url = f"{proxy_type}://{proxy_url}"
                
                proxies = {
                    'http': proxy_url,
                    'https': proxy_url
                }
                proxy_display = proxy_url.split('@')[-1] if '@' in proxy_url else proxy_url
                print(f"Using {proxy_type.upper()} proxy: {proxy_display}")
        
        print(f"Fetching: {url}")
        response = requests.get(url, timeout=30, proxies=proxies)
        response.raise_for_status()
        
        # Write to cache
        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        # Build metadata
        metadata = {
            "source": url,
            "source_type": "remote",
            "cached_at": datetime.now().isoformat(),
            "hash": compute_file_hash(cache_path),
            "http_headers": {
                "etag": response.headers.get('ETag', ''),
                "last_modified": response.headers.get('Last-Modified', ''),
            }
        }
        
        # Note: proxy_name is stored at the alias level, not in fetch metadata
        
        return True, metadata
        
    except requests.RequestException as e:
        utils.error(f"Failed to fetch {url}: {e}")
        return False, None
    except Exception as e:
        utils.error(f"Error caching file: {e}")
        return False, None


def cache_local_file(source_path: str, cache_path: str) -> Tuple[bool, Optional[Dict]]:
    """Cache a local .xts file.
    
    Args:
        source_path: Absolute path to source file
        cache_path: Where to cache the file
        
    Returns:
        Tuple of (success, metadata_dict)
    """
    try:
        # Copy to cache
        shutil.copy2(source_path, cache_path)
        
        # Build metadata
        stat = os.stat(source_path)
        metadata = {
            "source": source_path,
            "source_type": "local",
            "cached_at": datetime.now().isoformat(),
            "hash": compute_file_hash(cache_path),
            "source_mtime": stat.st_mtime,
        }
        
        return True, metadata
        
    except Exception as e:
        utils.error(f"Failed to cache {source_path}: {e}")
        return False, None


def check_for_updates(alias_name: str, metadata: Dict) -> Tuple[bool, str]:
    """Check if alias source has updates available.
    
    Args:
        alias_name: Name of alias
        metadata: Metadata dict for this alias
        
    Returns:
        Tuple of (has_update, status_message)
    """
    source = metadata.get("source")
    source_type = metadata.get("source_type")
    
    if source_type == "remote":
        return check_remote_updates(metadata)
    elif source_type == "local":
        return check_local_updates(metadata)
    else:
        return False, "Unknown source type"


def check_remote_updates(metadata: Dict) -> Tuple[bool, str]:
    """Check if remote URL has updates."""
    if not REQUESTS_AVAILABLE:
        return False, "requests not available"
    
    url = metadata.get("source")
    cached_etag = metadata.get("http_headers", {}).get("etag", "")
    
    # Get proxy config from proxy name if available
    proxy_config = None
    proxies = None
    proxy_name = metadata.get('proxy_name')
    
    if proxy_name:
        proxy_config = get_proxy_config(proxy_name)
        if proxy_config:
            proxy_url = proxy_config.get('proxy')
            username = proxy_config.get('username')
            password = proxy_config.get('password')
            
            if proxy_url:
                # If username/password available, embed in proxy URL
                if username and password:
                    if '://' in proxy_url:
                        scheme, rest = proxy_url.split('://', 1)
                        proxy_url = f"{scheme}://{username}:{password}@{rest}"
                    else:
                        proxy_url = f"http://{username}:{password}@{proxy_url}"
                
                proxies = {'http': proxy_url, 'https': proxy_url}
    
    try:
        # HEAD request to check headers without downloading
        response = requests.head(url, timeout=10, allow_redirects=True, proxies=proxies)
        response.raise_for_status()
        
        current_etag = response.headers.get('ETag', '')
        
        if current_etag and cached_etag and current_etag != cached_etag:
            return True, "ETag changed"
        
        # If no ETag, check Last-Modified
        cached_mtime = metadata.get("http_headers", {}).get("last_modified", "")
        current_mtime = response.headers.get('Last-Modified', '')
        
        if current_mtime and cached_mtime and current_mtime != cached_mtime:
            return True, "Last-Modified changed"
        
        return False, "Up to date"
        
    except Exception as e:
        # Can't check - assume no update
        return False, f"Check failed: {e}"


def check_local_updates(metadata: Dict) -> Tuple[bool, str]:
    """Check if local file has been modified."""
    source_path = metadata.get("source")
    
    if not os.path.exists(source_path):
        return False, "Source file missing"
    
    try:
        current_mtime = os.stat(source_path).st_mtime
        cached_mtime = metadata.get("source_mtime", 0)
        
        if current_mtime > cached_mtime:
            # Check if content actually changed
            current_hash = compute_file_hash(source_path)
            cached_hash = metadata.get("hash", "")
            
            if current_hash != cached_hash:
                return True, "File modified"
        
        return False, "Up to date"
        
    except Exception as e:
        return False, f"Check failed: {e}"


def load_metadata() -> Dict:
    """Load metadata for all cached files."""
    if not os.path.exists(METADATA_FILE):
        return {}
    
    try:
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def save_metadata(metadata: Dict):
    """Save metadata for all cached files."""
    ensure_dirs()
    try:
        with open(METADATA_FILE, 'w') as f:
            json.dump(metadata, f, indent=2)
    except Exception as e:
        utils.warning(f"Failed to save metadata: {e}")


def load_proxies() -> Dict:
    """Load proxy configurations."""
    if not os.path.exists(PROXIES_FILE):
        return {}
    
    try:
        with open(PROXIES_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def save_proxies(proxies: Dict):
    """Save proxy configurations."""
    ensure_dirs()
    try:
        with open(PROXIES_FILE, 'w') as f:
            json.dump(proxies, f, indent=2)
    except Exception as e:
        utils.warning(f"Failed to save proxies: {e}")


def add_proxy(name: str, proxy: str, proxy_type: str = 'http', username: Optional[str] = None, password: Optional[str] = None) -> bool:
    """Add or update a proxy configuration.
    
    Args:
        name: Proxy name/identifier
        proxy: Proxy server (host:port or protocol://host:port)
        proxy_type: Proxy type (http, https, socks5, ssh)
        username: Optional proxy username
        password: Optional proxy password
        
    Returns:
        True on success, False on failure
    """
    # Validate proxy type
    valid_types = ['http', 'https', 'socks5', 'ssh']
    if proxy_type.lower() not in valid_types:
        utils.error(f"Invalid proxy type '{proxy_type}'. Must be one of: {', '.join(valid_types)}")
        return False
    
    ensure_dirs()
    proxies = load_proxies()
    
    proxies[name] = {
        'proxy': proxy,
        'type': proxy_type.lower(),
        'username': username,
        'password': password
    }
    
    save_proxies(proxies)
    utils.success(f"✓ Added {proxy_type.upper()} proxy '{name}' -> {proxy}")
    return True


def list_proxies() -> Dict:
    """List all proxy configurations.
    
    Returns:
        Dictionary of proxy configurations
    """
    return load_proxies()


def remove_proxy(name: str) -> bool:
    """Remove a proxy configuration.
    
    Args:
        name: Proxy name to remove
        
    Returns:
        True on success, False if proxy not found
    """
    proxies = load_proxies()
    
    if name not in proxies:
        utils.warning(f"Proxy '{name}' not found")
        return False
    
    del proxies[name]
    save_proxies(proxies)
    utils.success(f"✓ Removed proxy '{name}'")
    return True


def get_proxy_config(proxy_name: str) -> Optional[Dict]:
    """Get proxy configuration by name.
    
    Args:
        proxy_name: Name of the proxy configuration
        
    Returns:
        Proxy config dict or None if not found
    """
    proxies = load_proxies()
    return proxies.get(proxy_name)


def add_alias(name: str, value: str, recursive: bool = False, proxy_name: Optional[str] = None):
    """Add or update an alias with universal caching.
    
    Args:
        name: Alias name
        value: Source path or URL
        recursive: If True and value is directory, scan recursively
        proxy_name: Optional proxy name (reference to proxy configuration)
    """
    ensure_dirs()
    
    # Load existing aliases and metadata
    aliases = list_aliases()
    all_metadata = load_metadata()
    
    # Get proxy config if proxy name provided
    proxy_config = None
    if proxy_name:
        proxy_config = get_proxy_config(proxy_name)
        if not proxy_config:
            utils.error(f"Proxy '{proxy_name}' not found. Add it first with: xts proxy add {proxy_name} <host:port>")
            return
    
    # Determine if value is URL, file, or directory
    if is_url(value):
        # Remote URL
        cache_path = get_cache_path(value, name)
        success, metadata = fetch_remote_file(value, cache_path, proxy_config)
        
        if success:
            aliases[name] = cache_path
            all_metadata[name] = metadata
            # Store proxy name reference in metadata
            if proxy_name:
                all_metadata[name]['proxy_name'] = proxy_name
            utils.success(f"✓ Added remote alias '{name}' -> {value}")
        else:
            utils.error(f"Failed to add alias '{name}'")
            return
            
    elif os.path.isfile(value):
        # Single file
        source_path = os.path.abspath(os.path.expanduser(value))
        
        if not source_path.endswith('.xts'):
            utils.error("File must have .xts extension")
            return
        
        if not os.path.exists(source_path):
            utils.error(f"File not found: {source_path}")
            return
        
        cache_path = get_cache_path(source_path, name)
        success, metadata = cache_local_file(source_path, cache_path)
        
        if success:
            aliases[name] = cache_path
            all_metadata[name] = metadata
            utils.success(f"✓ Added local alias '{name}' -> {source_path}")
        else:
            utils.error(f"Failed to add alias '{name}'")
            return
            
    elif os.path.isdir(value):
        # Directory - find .xts files
        dir_path = os.path.abspath(os.path.expanduser(value))
        xts_files = find_xts_files(dir_path, recursive)
        
        if not xts_files:
            utils.warning(f"No .xts files found in {dir_path}")
            return
        
        print(f"\nFound {len(xts_files)} .xts file(s):")
        for i, file in enumerate(xts_files, 1):
            rel_path = os.path.relpath(file, dir_path)
            print(f"  {i}. {rel_path}")
        
        print()
        response = input(f"Add all {len(xts_files)} files as separate aliases? (y/n): ").strip().lower()
        
        if response != 'y':
            utils.info("Cancelled")
            return
        
        # Add each file
        added = 0
        for file in xts_files:
            # Generate alias name from filename
            filename = os.path.basename(file)
            file_alias = os.path.splitext(filename)[0]
            
            # Handle duplicates
            if file_alias in aliases:
                file_alias = f"{file_alias}_{added + 1}"
            
            cache_path = get_cache_path(file, file_alias)
            success, metadata = cache_local_file(file, cache_path)
            
            if success:
                aliases[file_alias] = cache_path
                all_metadata[file_alias] = metadata
                print(f"  ✓ Added '{file_alias}' -> {file}")
                added += 1
        
        utils.success(f"\n✓ Added {added} aliases")
        
    else:
        utils.error(f"Invalid path: {value}")
        return
    
    # Save aliases and metadata
    with open(ALIAS_FILE, 'w') as f:
        json.dump(aliases, f, indent=2)
    save_metadata(all_metadata)


def list_aliases(check_updates: bool = False) -> Dict:
    """List all aliases with status indicators.
    
    Args:
        check_updates: If True, check for updates (slower)
        
    Returns:
        Dictionary of aliases
    """
    if not os.path.exists(ALIAS_FILE):
        return {}
    
    with open(ALIAS_FILE, 'r') as f:
        aliases = json.load(f)
    
    if check_updates:
        metadata = load_metadata()
        
        print("\nChecking for updates...\n")
        
        for name in aliases:
            if name in metadata:
                has_update, msg = check_for_updates(name, metadata[name])
                
                if has_update:
                    print(f"  {AliasStatus.UPDATE_AVAILABLE} {name} - Update available")
                else:
                    source_type = metadata[name].get("source_type", "unknown")
                    type_icon = AliasStatus.REMOTE if source_type == "remote" else AliasStatus.LOCAL
                    print(f"  {AliasStatus.UP_TO_DATE} {name} [{type_icon}]")
    
    return aliases


def refresh_alias(name: str) -> bool:
    """Refresh an alias from its source.
    
    Args:
        name: Alias name to refresh
        
    Returns:
        True if refreshed successfully
    """
    aliases = list_aliases()
    metadata = load_metadata()
    
    if name not in aliases:
        utils.error(f"Alias '{name}' not found")
        return False
    
    if name not in metadata:
        utils.error(f"No metadata for alias '{name}'")
        return False
    
    meta = metadata[name]
    source = meta.get("source")
    source_type = meta.get("source_type")
    cache_path = aliases[name]
    
    print(f"Refreshing '{name}' from {source}...")
    
    if source_type == "remote":
        # Get proxy config from proxy name if available
        proxy_config = None
        proxy_name = meta.get('proxy_name')
        if proxy_name:
            proxy_config = get_proxy_config(proxy_name)
            if not proxy_config:
                utils.warning(f"Proxy '{proxy_name}' not found, continuing without proxy")
        success, new_meta = fetch_remote_file(source, cache_path, proxy_config)
        # Preserve proxy_name in refreshed metadata
        if success and proxy_name:
            new_meta['proxy_name'] = proxy_name
    elif source_type == "local":
        if not os.path.exists(source):
            utils.warning(f"Source file missing: {source}")
            utils.info(f"Using cached version at: {cache_path}")
            return False
        success, new_meta = cache_local_file(source, cache_path)
    else:
        utils.error(f"Unknown source type: {source_type}")
        return False
    
    if success:
        metadata[name] = new_meta
        save_metadata(metadata)
        utils.success(f"✓ Refreshed '{name}'")
        return True
    else:
        utils.error(f"Failed to refresh '{name}'")
        return False


def remove_alias(name: str):
    """Remove an alias.
    
    Args:
        name: Alias name to remove
    """
    if not os.path.exists(ALIAS_FILE):
        return
    
    with open(ALIAS_FILE, 'r') as f:
        aliases = json.load(f)
    
    if name not in aliases:
        utils.warning(f"Alias '{name}' not found")
        return
    
    # Remove cache file
    cache_path = aliases[name]
    if os.path.exists(cache_path):
        try:
            os.remove(cache_path)
        except Exception:
            pass
    
    # Remove from aliases
    del aliases[name]
    
    with open(ALIAS_FILE, 'w') as f:
        json.dump(aliases, f, indent=2)
    
    # Remove metadata
    metadata = load_metadata()
    if name in metadata:
        del metadata[name]
        save_metadata(metadata)
    
    utils.success(f"✓ Removed alias '{name}'")


def clean_broken_aliases():
    """Find and optionally remove broken aliases."""
    aliases = list_aliases()
    metadata = load_metadata()
    
    broken = []
    
    for name, cache_path in aliases.items():
        if not os.path.exists(cache_path):
            broken.append((name, "Cache file missing"))
        elif name in metadata:
            meta = metadata[name]
            if meta.get("source_type") == "local":
                source = meta.get("source")
                if source and not os.path.exists(source):
                    broken.append((name, "Source file missing"))
    
    if not broken:
        utils.success("✓ No broken aliases found")
        return
    
    print(f"\nFound {len(broken)} broken alias(es):")
    for name, reason in broken:
        print(f"  ✗ {name} - {reason}")
    
    print()
    response = input("Remove broken aliases? (y/n): ").strip().lower()
    
    if response == 'y':
        for name, _ in broken:
            remove_alias(name)
        utils.success(f"✓ Removed {len(broken)} broken aliases")
