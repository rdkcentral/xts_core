# XTS Command History & Recall

## Quick Command Recall

### 1. **Arrow Keys** (Simplest)
- **↑ (Up Arrow)** - Recall previous command
- **↓ (Down Arrow)** - Move forward in history
- Press up arrow, then edit the command, then Enter

```bash
$ xts allocator list
{"slots":[]}
$ ↑  # Brings back: xts allocator list
# Edit to: xts allocator list_free
```

### 2. **Ctrl+R** (Reverse Search)
Search through your command history:
```bash
$ <Ctrl+R>
(reverse-i-search)`alloc': xts allocator alloc_by_id user@example.com 1 2h
```
- Type to search
- Ctrl+R again to cycle through matches
- Enter to execute
- Ctrl+C to cancel

### 3. **History Expansion**
Bash shortcuts for command reuse:

```bash
# Repeat last command
$ xts allocator list
$ !!  # Runs: xts allocator list

# Repeat last command with sudo
$ !!

# Use last argument from previous command
$ xts allocator alloc_by_id user@example.com 5 2h
$ xts allocator release !$  # !$ = "2h" (last arg)
# Better: xts allocator release user@example.com 5

# Use specific argument
$ xts allocator alloc_by_id user@example.com 5 2h
$ xts allocator release !:2 !:3  # !:2 = user@example.com, !:3 = 5

# Repeat last command starting with "xts"
$ !xts

# Repeat last command containing "allocator"
$ !?allocator
```

### 4. **Edit Last Command**
Quickly fix typos:
```bash
$ xts allocator alloc_by_id usr@example.com 5 2h  # Typo: "usr"
$ ^usr^user  # Replaces usr with user and runs
# Executes: xts allocator alloc_by_id user@example.com 5 2h
```

### 5. **History Command**
View and reuse from history:
```bash
# Show recent commands
$ history 20

# Execute command by number
$ !542  # Runs command #542 from history

# Show only xts commands
$ history | grep xts
```

## Enhanced Bash Configuration

Add these to your `~/.bashrc` for better history:

```bash
# Increase history size
export HISTSIZE=10000
export HISTFILESIZE=20000

# Don't store duplicate commands
export HISTCONTROL=ignoredups:erasedups

# Append to history (don't overwrite)
shopt -s histappend

# Save multi-line commands as one entry
shopt -s cmdhist

# Real-time history sharing across sessions
PROMPT_COMMAND="history -a; history -n"

# Enable Ctrl+S for forward search (reverse of Ctrl+R)
stty -ixon
```

After adding these, reload:
```bash
source ~/.bashrc
```

## XTS-Specific Aliases

Create bash aliases for common xts commands:

```bash
# Add to ~/.bashrc
alias xa='xts allocator'
alias xal='xts allocator list'
alias xalf='xts allocator list_free'
alias xaa='xts allocator alloc_by_id'
alias xar='xts allocator release'

# Now you can use:
$ xal  # Instead of: xts allocator list
$ xaa user@example.com 5 2h  # Allocate device 5
```

## Readline (inputrc) Enhancements

Add to `~/.inputrc` for better tab completion behavior:

```bash
# Create/edit ~/.inputrc
$ nano ~/.inputrc
```

Add these lines:
```
# Show all completions immediately
set show-all-if-ambiguous on

# Case-insensitive completion
set completion-ignore-case on

# Colored completion
set colored-stats on
set colored-completion-prefix on

# Menu completion - cycle through options with tab
"\t": menu-complete
"\e[Z": menu-complete-backward

# Show completion type indicators
set visible-stats on

# Immediately show completion matches
set show-all-if-unmodified on
```

Reload:
```bash
$ bind -f ~/.inputrc
```

## Practical Workflow Examples

### Example 1: Allocate, Test, Release
```bash
# Step 1: Allocate
$ xts allocator alloc_by_id user@example.com 5 2h
{"status":"success","device_id":5}

# Step 2: Use it (remember the command)
$ ↑  # Recall allocation command
# Edit to release: xts allocator release user@example.com 5
```

### Example 2: List, Then Allocate Specific Device
```bash
# See available devices
$ xts allocator list_free

# Pick one, reuse the alias name with tab completion
$ xts allocator alloc_<TAB>  # Completes to alloc_by_id, alloc_by_platform, etc.
```

### Example 3: Repeat with Modifications
```bash
# Allocate device 5
$ xts allocator alloc_by_id user@example.com 5 2h

# Release it
$ ↑  # Recall
# Change "alloc_by_id" to "release" and remove "2h"
$ xts allocator release user@example.com 5
```

## Advanced: fzf Integration (Optional)

For even better history search, install [fzf](https://github.com/junegunn/fzf):

```bash
# Install
$ sudo apt install fzf  # or: git clone https://github.com/junegunn/fzf.git ~/.fzf && ~/.fzf/install

# Add to ~/.bashrc
[ -f ~/.fzf.bash ] && source ~/.fzf.bash
```

Now:
- **Ctrl+R** - Interactive fuzzy history search with preview
- **Ctrl+T** - Fuzzy file finder
- **Alt+C** - Fuzzy directory changer

## Tips & Tricks

1. **Quick Edit**: Start typing a command, then ↑ to search history for commands starting with those characters

2. **Job Control**: 
   ```bash
   $ xts allocator list  # Takes a while...
   <Ctrl+Z>  # Suspend
   $ bg      # Continue in background
   $ fg      # Bring back to foreground
   ```

3. **Command Substitution**:
   ```bash
   # Use output of one command in another
   $ DEVICE=$(xts allocator list | jq -r '.slots[0].id')
   $ xts allocator alloc_by_id user@example.com $DEVICE 2h
   ```

4. **For Loops for Batch Operations**:
   ```bash
   # Release multiple devices
   $ for id in 1 2 3; do xts allocator release user@example.com $id; done
   ```

## Summary

**Fastest methods for command recall:**

| Action | Method | Example |
|--------|--------|---------|
| Recall last command | `↑` | Press up arrow |
| Search history | `Ctrl+R` | Ctrl+R, type "alloc" |
| Repeat last command | `!!` | `!!` |
| Fix typo | `^old^new` | `^usr^user` |
| Use last argument | `!$` | `command !$` |

**After running a command, you can:**
1. Press `↑` to recall it
2. Press `Ctrl+R` and search for it
3. Type the start of the command and press `↑` to search matching history

Unfortunately, **tab completion cannot recall history** - that's a shell limitation. But the methods above are faster than tab-tab anyway!
