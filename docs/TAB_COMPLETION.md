# XTS Tab Completion

Tab completion is now available for the `xts` command in bash.

## Installation

The completion script is automatically installed to `~/.xts/xts-completion.bash`

### Auto-load on shell startup

Add this line to your `~/.bashrc`:
```bash
source ~/.xts/xts-completion.bash
```

Then reload your shell:
```bash
source ~/.bashrc
```

### Manual loading (current session only)

```bash
source ~/.xts/xts-completion.bash
```

## Usage Examples

### 1. Complete main commands and aliases
Type `xts ` then press **TAB** twice:
```
$ xts <TAB><TAB>
alias  allocator  hello_world  xts_allocator
```

### 2. Complete partial matches
Type `xts al` then press **TAB**:
```
$ xts al<TAB>
$ xts alias    # or allocator if unique
```

### 3. Complete alias subcommands
Type `xts alias ` then press **TAB** twice:
```
$ xts alias <TAB><TAB>
add  list  remove
```

### 4. File completion for adding aliases
Type `xts alias add ` then press **TAB**:
```
$ xts alias add <TAB>
# Shows files and directories
```

### 5. Complete existing alias names for removal
Type `xts alias remove ` then press **TAB** twice:
```
$ xts alias remove <TAB><TAB>
allocator  hello_world  xts_allocator
```

## How It Works

The completion script:
- Reads available aliases from `~/.xts/aliases.json`
- Provides context-aware completions based on command position
- Suggests files/directories for `xts alias add`
- Suggests existing alias names for `xts alias remove`

## Troubleshooting

**Tab completion not working?**

1. Check if script is sourced:
   ```bash
   complete -p xts
   ```
   Should show: `complete -F _xts_completion xts`

2. Reload the completion:
   ```bash
   source ~/.xts/xts-completion.bash
   ```

3. Check if aliases.json exists:
   ```bash
   ls -la ~/.xts/aliases.json
   ```

**Completions out of date?**

After adding/removing aliases, tab completion updates automatically on the next TAB press (reads from `~/.xts/aliases.json` dynamically).
