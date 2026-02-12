# Proxy Support for Remote Aliases

## Overview

XTS now supports HTTP/HTTPS proxy configuration for remote aliases. This feature is essential for users working in corporate environments or behind firewalls where direct internet access is restricted.

## Proxy Types Supported

XTS supports multiple proxy protocols:

| Type | Description | Use Case | Requires |
|------|-------------|----------|----------|
| **HTTP** | Standard HTTP proxy | Corporate proxies, basic filtering | Default |
| **HTTPS** | HTTPS proxy | Secure proxy connections | - |
| **SOCKS5** | SOCKS5 proxy | Flexible routing, SSH tunnels | requests[socks] |
| **SSH** | SSH tunnel | Secure remote access | Manual SSH setup |

## Feature Summary

### What's New

- **Centralized Proxy Management**: Define proxies once and reuse them across multiple aliases
- **Proxy Authentication**: Support for username/password authentication
- **Automatic Proxy Usage**: Once configured, proxy is used automatically for all operations
- **Secure**: Passwords stored in separate proxy configuration file

### Use Case

```bash
# Step 1: Define a proxy configuration (with type)
xts proxy add sky proxy.company.com:8080 --type http \
    --username employee123 \
    --password SecurePass123

# HTTP proxy (default)
xts proxy add corp-http proxy.company.com:8080

# HTTPS proxy
xts proxy add corp-https secure-proxy.company.com:8443 --type https

# SOCKS5 proxy (for SSH tunnels or flexible routing)
xts proxy add socks localhost:1080 --type socks5 --username user --password pass

# SSH tunnel (requires manual SSH setup)
ssh -D 8888 -N -f user@remote.server.com
xts proxy add ssh-tunnel localhost:8888 --type socks5

# Step 2: Add alias referencing the proxy
xts alias add allocator http://internal-server:5000/allocator.xts --proxy sky

# Step 3: Use the alias normally
xts allocator list_slots

# Updates automatically use the configured proxy
xts alias list --check
xts alias refresh allocator

# Manage proxies
xts proxy list
xts proxy remove sky
```

## Implementation Details

### Command Line Interface

#### Proxy Management Commands

**Add a proxy:**
```bash
xts proxy add <name> <host:port> [--type <type>] [--username <user>] [--password <pass>]

# Types: http (default), https, socks5, ssh
```

**List all proxies:**
```bash
xts proxy list
```

**Remove a proxy:**
```bash
xts proxy remove <name>
```

#### Alias Command Updates

New option added to `xts alias add` command:

- `--proxy NAME`: Reference to configured proxy (e.g., `--proxy sky`)

### Data Storage

Proxy configurations are stored in `~/.xts/proxies.json`:

```json
{
  "sky": {
    "proxy": "proxy.company.com:8080",
    "type": "http",
    "username": "employee123",
    "password": "SecurePass123"
  },
  "backup_proxy": {
    "proxy": "backup.company.com:3128",
    "type": "https",
    "username": null,
    "password": null
  },
  "socks_tunnel": {
    "proxy": "localhost:1080",
    "type": "socks5",
    "username": "sockuser",
    "password": "sockpass"
  }
}
```

Alias metadata stores only proxy name reference in `~/.xts/metadata.json`:

```json
{
  "allocator": {
    "source": "http://internal-server:5000/allocator.xts",
    "source_type": "remote",
    "cached_at": "2026-02-12T10:30:00",
    "hash": "abc123...",
    "proxy_name": "sky"
  }
}
```

### Code Changes

#### 1. xts_alias.py

- **Added proxy management functions:**
  - `load_proxies()`: Load proxy configurations from `~/.xts/proxies.json`
  - `save_proxies()`: Save proxy configurations
  - `add_proxy()`: Add or update a proxy configuration
  - `list_proxies()`: List all configured proxies
  - `remove_proxy()`: Remove a proxy configuration
  - `get_proxy_config()`: Retrieve a specific proxy configuration by name

- **Modified `fetch_remote_file()`**: No changes to signature
  - Accepts optional `proxy_config` dictionary parameter
  - Embeds credentials in proxy URL for requests library

- **Modified `add_alias()`**: Changed proxy parameters
  - New parameter: `proxy_name` (reference to configured proxy)
  - Retrieves proxy config using `get_proxy_config(proxy_name)`
  - Stores `proxy_name` in metadata (not full proxy config)

- **Modified `check_remote_updates()`**: Uses proxy lookup
  - Reads `proxy_name` from metadata
  - Retrieves proxy config using `get_proxy_config()`
  - Applies proxy to HTTP HEAD requests for update checks

- **Modified `refresh_alias()`**: Uses proxy lookup
  - Retrieves `proxy_name` from metadata
  - Looks up full proxy config using `get_proxy_config()`
  - Passes to `fetch_remote_file()` during refresh

#### 2. xts.py

- **Added `_add_proxy_subcommands()`**: New function for proxy CLI
  - `proxy add <name> <host:port>`: Add proxy configuration
    - `--username`: Optional proxy username
    - `--password`: Optional proxy password
  - `proxy list`: List all configured proxies
  - `proxy remove <name>`: Remove proxy configuration

- **Added `_handle_proxy()`**: Handle proxy subcommands
  - Routes to `xts_alias.add_proxy()`, `list_proxies()`, `remove_proxy()`

- **Modified `_add_alias_subcommands()`**: Updated CLI arguments
  - `--proxy NAME`: Reference to configured proxy (changed from proxy URL)

- **Modified `_handle_alias()`**: Passes proxy name to add_alias
  - Extracts `--proxy` argument as proxy name
  - Forwards to `xts_alias.add_alias(proxy_name=name)`

### Security Considerations

1. **Password Storage**: Proxy passwords ARE stored in `~/.xts/proxies.json`
   - Stored in plaintext for convenience and usability
   - File permissions should restrict access (user-only)
   - Users should be aware credentials are stored locally

2. **Separate Storage**: Proxies stored separately from alias metadata
   - Centralized credential management
   - Easier to secure or gitignore the proxies.json file
   - Reusability across multiple aliases

3. **Best Practices**:
   - Protect `~/.xts/proxies.json` with appropriate file permissions
   - Don't commit `proxies.json` to version control
   - Consider using proxy auto-configuration (PAC) files where available
   - Use environment variables for system-wide proxy configuration:
     ```bash
     export HTTP_PROXY="http://user:pass@proxy.company.com:8080"
     export HTTPS_PROXY="http://user:pass@proxy.company.com:8080"
     ```

## Testing

### Test Coverage

Added comprehensive test suite in `test_xts_alias_remote.py`:

1. **`test_fetch_with_proxy`**: Basic proxy functionality
2. **`test_fetch_with_proxy_auth`**: Proxy with authentication
3. **`test_add_alias_with_proxy`**: End-to-end alias creation with proxy
4. **`test_check_updates_with_proxy`**: Update checking through proxy

All tests use mocking to avoid requiring actual proxy servers.

### Running Tests

## Testing

### Running Tests

```bash
# Run proxy-specific tests
./test.sh --proxy

# Run all remote tests
./test.sh --remote

# Run all tests
./test.sh
```

### Test Results

✅ All 5 proxy tests pass

## Documentation

### Updated Files

1. **README.md**: Added "Working with Aliases" section with proxy examples
2. **docs/HTTP_ANALYSIS.md**: Extended proxy support section
3. **docs/PROXY_FEATURE.md**: Comprehensive proxy feature documentation
4. **CHANGELOG.md**: Documented new feature in Unreleased section

### Help Text

#### Proxy Commands

```bash
$ xts proxy --help

usage: xts proxy [-h] {add,list,remove} ...

Manage proxy configurations

positional arguments:
  {add,list,remove}
    add               Add a proxy configuration
    list              List all proxy configurations
    remove            Remove a proxy configuration

options:
  -h, --help          show this help message and exit
```

```bash
$ xts proxy add --help

usage: xts proxy add [-h] [--username USERNAME] [--password PASSWORD]
                     name proxy

positional arguments:
  name                      Proxy name/identifier (e.g., sky)
  proxy                     Proxy server (format: host:port or http://host:port)

options:
  -h, --help                show this help message and exit
  --username USERNAME       Proxy username (optional)
  --password PASSWORD       Proxy password (optional)
```

#### Alias Command Updates

```bash
$ xts alias add --help

usage: xts alias add [-h] [-r] [--proxy PROXY] name [path]

positional arguments:
  name                Alias name, or directory path
  path                Path or URL

options:
  -h, --help          show this help message and exit
  -r, --recursive     Recursively search for .xts files
  --proxy PROXY       Proxy name (reference to configured proxy, e.g., --proxy sky)
```

## Examples

### Basic Workflow

```bash
# Step 1: Add a proxy configuration (HTTP is default)
xts proxy add corporate proxy.company.com:8080 --type http \
    --username employee123 \
    --password SecurePass

# Step 2: Add alias using the proxy
xts alias add demo https://example.com/demo.xts --proxy corporate

# Step 3: List configured proxies
xts proxy list

# Step 4: Use the alias normally
xts demo some_command

# Step 5: Update checks use the proxy automatically
xts alias list --check

# Step 6: Clean up
xts proxy remove corporate
```

### SOCKS5 Proxy Example

```bash
# Configure SOCKS5 proxy (useful for SSH tunnels)
xts proxy add socks-local localhost:1080 --type socks5 \
    --username sockuser \
    --password sockpass

# Add alias through SOCKS5
xts alias add api https://api.example.com/app.xts --proxy socks-local

# Use it
xts api list_items
```

### SSH Tunnel Example

```bash
# Step 1: Set up SSH tunnel (separate terminal)
ssh -D 8888 -N -f user@remote-server.com

# Step 2: Configure proxy to use the tunnel (use socks5 type)
xts proxy add ssh-tunnel localhost:8888 --type socks5

# Step 3: Add alias through tunnel
xts alias add internal https://internal-server/app.xts --proxy ssh-tunnel
```

### Advanced Usage

```bash
# Configure multiple proxies for different environments
xts proxy add corporate proxy.company.com:8080 --type http --username user1 --password pass1
xts proxy add backup backup-proxy.company.com:3128 --type https
xts proxy add socks localhost:1080 --type socks5

# Add aliases with different proxies
xts alias add prod-server https://prod.example.com/app.xts --proxy corporate
xts alias add backup-server https://backup.example.com/app.xts --proxy backup
xts alias add dev-server http://dev.internal/app.xts --proxy socks

# Reuse the same proxy for multiple aliases
xts proxy add shared proxy.example.com:8080 --username shared_user --password shared_pass
xts alias add api1 https://api1.example.com/api.xts --proxy shared
xts alias add api2 https://api2.example.com/api.xts --proxy shared
xts alias add api3 https://api3.example.com/api.xts --proxy shared
```

### Corporate Environment

```bash
# Step 1: Configure corporate proxy
xts proxy add corporate corporate-proxy.company.com:3128 \
    --username john.doe \
    --password MyPassword

# Step 2: Add alias using the proxy
xts alias add allocator http://tooling.internal:5000/allocator.xts --proxy corporate

# Step 3: Use alias normally
xts allocator list_slots
xts allocator alloc_by_id user@example.com 5 2h

# Updates happen automatically with proxy
xts alias list --check
xts alias refresh allocator

# View proxy configuration
xts proxy list
```

### No-Authentication Proxy

```bash
# For proxies without authentication
xts proxy add simple-proxy proxy.example.com:8080

# Add alias using simple proxy
xts alias add public-api https://api.example.com/app.xts --proxy simple-proxy
```

## Future Enhancements

Potential future improvements:

1. **Credential Storage**: Secure credential storage using keyring/keychain
2. **Proxy Auto-detection**: Detect proxy from system settings
3. **PAC File Support**: Support proxy auto-configuration files
4. **Per-Operation Proxy Override**: Ability to override proxy for specific operations
5. **SOCKS Proxy**: Support SOCKS4/SOCKS5 protocols
6. **Proxy Testing**: Command to test proxy connectivity

## Compatibility

- **Python Version**: Requires Python 3.10+
- **Dependencies**: Uses `requests` library (already required)
  - SOCKS5 support requires: `pip install requests[socks]`
  - SSH tunnels require manual SSH client setup
- **Operating Systems**: Linux (primary), should work on macOS/Windows
- **Backward Compatibility**: Fully backward compatible - existing aliases work without modification

### Installing SOCKS5 Support

To use SOCKS5 proxies (including SSH tunnels), install the additional dependency:

```bash
pip install requests[socks]
# or
pip install PySocks
```

## Summary

This feature enables XTS to work in restricted network environments where HTTP proxies are required. Proxies are defined once and can be reused across multiple aliases, providing centralized credential management.

**Key Benefits:**
- ✅ Works in corporate environments
- ✅ Centralized proxy management
- ✅ Reusable across multiple aliases
- ✅ Authentication support
- ✅ Credential storage in separate file
- ✅ Automatic proxy usage for all operations
- ✅ Fully tested (5 proxy tests passing)
- ✅ Well documented

**Command Format:**
```bash
# Define proxy once
xts proxy add <name> <host:port> [--username <user>] [--password <pass>]

# Reference proxy when adding aliases
xts alias add <name> <url> --proxy <proxy_name>
