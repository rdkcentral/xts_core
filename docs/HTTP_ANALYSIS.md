# HTTP Repository Analysis

Analyze remote codebases via HTTP/HTTPS without cloning the repository first.

## Quick Start

```bash
# Analyze any GitHub repository
xts analyze https://github.com/user/repo --output prompt.txt

# View detailed analysis
xts analyze https://github.com/user/repo --verbose

# Get JSON output
xts analyze https://github.com/rdkcentral/xts_core --json
```

## Supported HTTP Sources

### GitHub Repositories

Full API integration for comprehensive analysis:

```bash
xts analyze https://github.com/rdkcentral/xts_core --verbose
```

**What gets fetched:**
- All files in repository root
- Subdirectory structure
- README, package.json, Makefile, etc.
- Python/Node.js/Go project files

**Output:**
```
Fetching remote repository from https://github.com/rdkcentral/xts_core...
  Downloaded: README.md
  Downloaded: pyproject.toml
  Downloaded: requirements.txt
  ...

======================================================================
  Repository Analysis
======================================================================

Source: Remote Repository (HTTP)
URL: https://github.com/rdkcentral/xts_core
Local Cache: /tmp/xts_analyze_xyz123
Language: python
Build System: poetry
Test Framework: detected
```

### GitLab Repositories

```bash
xts analyze https://gitlab.com/user/project --verbose
```

Uses GitLab API for file discovery.

### Generic HTTP Servers

For code hosted on any HTTP server:

```bash
xts analyze https://example.com/code/ --output prompt.txt
```

**What gets fetched:**
Attempts to download common project files:
- README.md, README.rst, README.txt
- package.json, package-lock.json
- requirements.txt, setup.py, pyproject.toml
- Makefile, CMakeLists.txt
- Cargo.toml, go.mod
- pom.xml, build.gradle
- jest.config.js, pytest.ini

## How It Works

### 1. URL Detection

```python
if url.startswith('http://') or url.startswith('https://'):
    # Fetch from remote
```

### 2. Source Detection

- **Preferred**: Shallow clone (`git clone --depth 1 --single-branch`)
- **Fallback**: Host API/file fetch when clone is unavailable or fails

### 3. Temporary Cache

Clones/downloads data to a temporary directory:

```
/tmp/xts_analyze_xyz123/
└── repo/
    ├── README.md
    ├── package.json
    ├── Makefile
    └── src/
        └── ...
```

### 4. Analysis

Same analysis as local repositories:
- Language detection
- Build system detection
- Test framework identification
- Command extraction

### 5. Cleanup

Temporary directory is automatically deleted after analysis completes.

## Examples

### Analyze Popular Projects

```bash
# React
xts analyze https://github.com/facebook/react --verbose

# Vue.js
xts analyze https://github.com/vuejs/vue --output vue_prompt.txt

# Django
xts analyze https://github.com/django/django --verbose

# XTS Allocator Server
xts analyze https://github.com/rdkcentral/xts_allocator_server --output allocator_prompt.txt
```

### Generate AI Prompt from Remote Code

```bash
# Step 1: Analyze
xts analyze https://github.com/user/awesome-project --output ai_prompt.txt

# Step 2: Open prompt
cat ai_prompt.txt
# Copy the content

# Step 3: Paste into Claude/ChatGPT/Gemini
# AI will generate an .xts file

# Step 4: Save as awesome-project.xts and use
xts alias add awesome awesome-project.xts
xts awesome build
```

## Comparison: Local vs Remote

### Local Analysis

```bash
# Must clone first
git clone https://github.com/user/repo
cd repo
xts analyze . --output prompt.txt
```

**Pros:**
- Full repository history
- All branches available
- Complete file structure

**Cons:**
- Requires disk space
- Takes time to clone
- Must have git installed

### Remote Analysis (HTTP)

```bash
# Direct analysis
xts analyze https://github.com/user/repo --output prompt.txt
```

**Pros:**
- No cloning needed
- Instant analysis
- No local disk usage
- Works without git

**Cons:**
- Only fetches necessary files
- Single branch (usually main/master)
- Depends on network connection

## Use Cases

### 1. Quick Inspection

Quickly check what commands a project uses:

```bash
xts analyze https://github.com/user/repo --verbose
```

### 2. Generate XTS for Remote Project

Create XTS configuration for a project you don't have locally:

```bash
xts analyze https://github.com/user/project --output prompt.txt
# Paste prompt into AI
# Get generated .xts file
```

### 3. CI/CD Integration

Analyze dependencies in CI pipeline:

```bash
#!/bin/bash
for repo in "${DEPENDENCIES[@]}"; do
    xts analyze "$repo" --json >> analysis_report.json
done
```

### 4. Repository Exploration

Explore unfamiliar codebases:

```bash
xts analyze https://github.com/org/unknown-project --verbose
```

Shows:
- Programming language
- Build system used
- Test framework
- Common commands
- Dependencies

## Advanced Usage

### Custom HTTP Headers

Not yet supported, but planned:

```bash
# Future feature
xts analyze https://private-server.com/repo \
    --header "Authorization: Bearer $TOKEN" \
    --output prompt.txt
```

### Rate Limiting

GitHub API fallback has rate limits:
- **Unauthenticated**: 60 requests/hour
- **Authenticated**: 5000 requests/hour

For heavy usage, set GitHub token:

```bash
# Future feature
export GITHUB_TOKEN="your_token_here"
xts analyze https://github.com/user/repo
```

### Proxy Support

Uses system HTTP proxy settings:

```bash
export HTTP_PROXY="http://proxy.example.com:8080"
export HTTPS_PROXY="https://proxy.example.com:8080"
xts analyze https://github.com/user/repo
```

## Troubleshooting

### Network Errors

```
Warning: shallow clone failed ...; falling back to HTTP/API fetch
```

**Solutions:**
- Check internet connection
- Verify URL is correct
- Try again (temporary network issue)
- Use local analysis instead

### Empty Analysis

```
Warning: Could not download README.md
Warning: Could not download package.json
```

**Cause:** Server doesn't have expected files

**Solutions:**
- Check if URL points to repository root
- Try with `/tree/main` or `/tree/master` removed from URL
- Use local clone for better results

### API Rate Limits

```
Warning: Could not fetch from GitHub API: 403 rate limit exceeded
```

**Solutions:**
- Wait for rate limit to reset (1 hour)
- Ensure `git` is available so shallow clone path is used
- Use local repository analysis

## Security Considerations

### Downloaded Content

- Repository content is cloned/downloaded to `/tmp/xts_analyze_*`
- Automatically deleted after analysis
- No code is executed during analysis
- Safe to analyze untrusted repositories

### Privacy

- HTTP requests include User-Agent: `XTS-Analyzer/1.0`
- No personal data is sent
- No analytics or tracking
- All analysis happens locally

## Performance

### Speed Comparison

| Method | Small Repo | Large Repo |
|--------|------------|------------|
| Local | < 1 second | 1-2 seconds |
| HTTP (GitHub) | 2-5 seconds | 5-15 seconds |
| HTTP (Generic) | 1-3 seconds | 3-10 seconds |

Factors:
- Network speed
- Repository size
- Number of files
- Server response time

### Bandwidth Usage

Typical analysis downloads:
- **Small project**: 50-500 KB
- **Medium project**: 0.5-2 MB
- **Large project**: 2-10 MB

Only essential files are fetched (not entire repository).

## Limitations

### Current Limitations

1. **No subdirectory analysis**: Only root and first-level subdirectories
2. **Limited file types**: Common project files only
3. **No git history**: Can't analyze commit messages or branches
4. **No authentication**: Public repositories only
5. **Fallback API rate limits**: GitHub limits apply only when shallow clone cannot be used

### Future Enhancements

- [ ] Authentication support (GitHub tokens, GitLab tokens)
- [ ] Private repository access
- [ ] Custom file patterns to fetch
- [ ] Subdirectory-specific analysis
- [ ] Caching of frequently analyzed repos
- [ ] Parallel file downloads
- [ ] Resume interrupted downloads

## Related Documentation

- [Repository Analyzer Overview](REPO_ANALYZER.md)
- [XTS Schema](SCHEMA.md)
- [AI Prompt Generation](REPO_ANALYZER.md#ai-integration-workflow)
