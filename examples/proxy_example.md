# Proxy Configuration Examples

This document provides examples of using XTS with proxy servers for remote alias management.

## Proxy Types Supported

XTS supports multiple proxy types:
- **HTTP** - Standard HTTP proxy (default)
- **HTTPS** - HTTPS proxy for secure connections
- **SOCKS5** - SOCKS5 proxy for more flexible routing
- **SSH** - SSH tunnel (requires manual SSH setup)

## Basic Proxy Usage

### Step 1: Add a Proxy Configuration

```bash
# Add an HTTP proxy (default type)
xts proxy add myproxy proxy.company.com:8080

# Add an HTTPS proxy
xts proxy add secure-proxy proxy.company.com:8443 --type https

# Add a SOCKS5 proxy
xts proxy add socks-proxy localhost:1080 --type socks5

# Add an SSH tunnel proxy (requires SSH setup first)
xts proxy add ssh-tunnel localhost:8888 --type ssh
```

### Step 2: Add Alias Using the Proxy

```bash
# Reference the proxy by name when adding an alias
xts alias add allocator http://internal-server:5000/allocator.xts --proxy myproxy
```

### With Proxy Authentication

```bash
# Add proxy with authentication
xts proxy add corp-proxy proxy.company.com:8080 \
    --username employee123 \
    --password SecurePass123

# Use the authenticated proxy
xts alias add allocator http://internal-server:5000/allocator.xts --proxy corp-proxy
```

## Real-World Scenarios

### Corporate Environment (HTTP Proxy)

Many corporate environments require HTTP traffic to go through authenticated proxy servers:

```bash
# Step 1: Configure proxy
xts proxy add corporate corporate-proxy.company.com:3128 \
    --type http \
    --username john.doe \
    --password MySecretPassword

# Step 2: Add alias using the proxy
xts alias add allocator http://tooling.internal:5000/allocator.xts --proxy corporate

# Step 3: Use the alias normally
xts allocator list_slots

# Update checking also uses the proxy automatically
xts alias list --check
```

### SOCKS5 Proxy Example

SOCKS5 proxies are useful for more flexible routing:

```bash
# Configure SOCKS5 proxy
xts proxy add socks-local localhost:1080 --type socks5 \
    --username sockuser \
    --password sockpass

# Add alias through SOCKS5 proxy
xts alias add api https://api.example.com/app.xts --proxy socks-local
```

### SSH Tunnel Setup

For SSH tunneling, you need to set up the tunnel manually first:

```bash
# Step 1: Set up SSH tunnel (in separate terminal)
ssh -D 8888 -N -f user@ssh-server.com

# Step 2: Configure proxy to use the tunnel
xts proxy add ssh-tunnel localhost:8888 --type socks5

# Step 3: Add alias using the tunnel
xts alias add remote https://remote-server.com/app.xts --proxy ssh-tunnel
```

### Dynamic IP/Port Proxies

If your proxy uses a non-standard port or IP address:

```bash
# Using IP address and custom port
xts proxy add custom-proxy 10.0.0.1:8888 --type http
xts alias add mytools http://192.168.1.100:8000/tools.xts --proxy custom-proxy

# Using full URL format
xts alias add mytools http://192.168.1.100:8000/tools.xts \
    --proxy http://proxy.local:3128
```

### Proxy Without Authentication

For proxies that don't require authentication:

```bash
xts alias add demo https://example.com/demo.xts \
    --proxy proxy.local:8080
```

## How It Works

1. **Storage**: Proxy configuration is stored in the alias metadata (`~/.xts/metadata.json`)
2. **Security**: Passwords are NOT stored in metadata for security reasons
3. **Automatic Use**: Once configured, the proxy is automatically used for:
   - Initial file fetch
   - Update checks (`xts alias list --check`)
   - Alias refresh (`xts alias refresh <name>`)

## Verifying Proxy Configuration

Check if your alias has proxy configuration:

```bash
# List all aliases
xts alias list

# Check the metadata file directly
cat ~/.xts/metadata.json
```

The metadata will show proxy configuration (without password):

```json
{
  "sky": {
    "source": "http://internal-server:5000/xts_allocator.xts",
    "source_type": "remote",
    "proxy": {
      "proxy": "proxy.company.com:8080",
      "username": "employee123"
    }
  }
}
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   ```
   Error: Failed to fetch http://example.com: Connection refused
   ```
   - Verify proxy address is correct
   - Check proxy is accessible from your network
   - Ensure proxy port is correct

2. **Authentication Failed**
   ```
   Error: 407 Proxy Authentication Required
   ```
   - Verify username and password are correct
   - Check if proxy requires special authentication

3. **Timeout**
   ```
   Error: Request timed out
   ```
   - Check network connectivity
   - Verify proxy server is responding
   - Try increasing timeout (contact system admin)

### Testing Proxy Connection

Test your proxy works with curl before using with XTS:

```bash
# Test proxy without auth
curl -x http://proxy.local:8080 http://example.com

# Test proxy with auth
curl -x http://user:pass@proxy.local:8080 http://example.com
```

## Security Considerations

- **Password Storage**: XTS does NOT store proxy passwords in metadata for security
- **Refresh Operations**: You may need to provide password again when refreshing aliases
- **Network Security**: Be aware that proxy servers can see your traffic
- **Use HTTPS**: When possible, use HTTPS URLs for alias sources

## Alternative: System Proxy

You can also configure system-wide proxy using environment variables:

```bash
export HTTP_PROXY="http://proxy.company.com:8080"
export HTTPS_PROXY="http://proxy.company.com:8080"
export NO_PROXY="localhost,127.0.0.1"

# Then XTS will use system proxy automatically
xts alias add demo http://example.com/demo.xts
```

**Note**: Per-alias proxy configuration (using `--proxy` option) takes precedence over system environment variables.
