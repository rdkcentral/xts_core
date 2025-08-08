import os
import hashlib
import json
import requests

CACHE_DIR = os.path.expanduser("~/.xts/cache")
ALIAS_FILE = os.path.expanduser("~/.xts/aliases.json")

def ensure_dirs():
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(ALIAS_FILE), exist_ok=True)

def is_url(s):
    return s.startswith("http://") or s.startswith("https://")

def fetch_url_to_cache(url):
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
    ensure_dirs()
    aliases = {}
    if os.path.exists(ALIAS_FILE):
        with open(ALIAS_FILE) as f:
            aliases = json.load(f)

    if arg in aliases:
        arg = aliases[arg]

    if is_url(arg):
        return fetch_url_to_cache(arg)

    return arg

def add_alias(name, value):
    ensure_dirs()
    aliases = {}
    if os.path.exists(ALIAS_FILE):
        with open(ALIAS_FILE) as f:
            aliases = json.load(f)
    aliases[name] = value
    with open(ALIAS_FILE, "w") as f:
        json.dump(aliases, f, indent=2)

def list_aliases():
    if not os.path.exists(ALIAS_FILE):
        return {}
    with open(ALIAS_FILE) as f:
        return json.load(f)

def remove_alias(name):
    if not os.path.exists(ALIAS_FILE):
        return
    with open(ALIAS_FILE) as f:
        aliases = json.load(f)
    if name in aliases:
        del aliases[name]
    with open(ALIAS_FILE, "w") as f:
        json.dump(aliases, f, indent=2)
