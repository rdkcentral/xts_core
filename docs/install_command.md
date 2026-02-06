# XTS Install Command - Feature Specification

## Overview
Add `xts install` command to set up XTS environment including bash completion and other requirements.

## Requirements

### Cross-Platform Support
- **Linux**: Standard bash completion
- **macOS**: Compatible with both bash and zsh (default on macOS Catalina+)
- **Detection**: Auto-detect OS and shell type

### Installation Tasks
1. **Bash/Zsh Completion**
   - Install completion script to `~/.xts/xts-completion.bash`
   - Auto-detect shell (bash vs zsh)
   - Add source line to appropriate rc file (`~/.bashrc`, `~/.bash_profile`, `~/.zshrc`)
   - macOS-specific: Handle both `/bin/bash` and `/bin/zsh`

2. **Dependencies**
   - Check for required Python packages
   - Check for `yaml-runner` installation
   - Optionally install missing dependencies

3. **Configuration**
   - Create `~/.xts/` directory structure
   - Initialize `aliases.json` if not exists
   - Set up default configuration

## Implementation Plan

### Command Structure
```bash
xts install [options]
```

### Options
- `--completion-only`: Install only bash/zsh completion
- `--check`: Check installation status without installing
- `--force`: Reinstall/overwrite existing installation
- `--shell <bash|zsh>`: Override auto-detection

### Example Usage
```bash
# Full installation
xts install

# Check what would be installed
xts install --check

# Install only completion
xts install --completion-only

# Force reinstall for zsh
xts install --force --shell zsh
```

### Installation Steps
1. Detect operating system (Linux, macOS, other)
2. Detect current shell
3. Create `~/.xts/` directory if missing
4. Copy completion script:
   - Bash: `~/.xts/xts-completion.bash`
   - Zsh: `~/.xts/xts-completion.zsh` (adapt from bash version)
5. Add source line to shell rc file:
   - Check if already present
   - Append if not present
   - Show instructions if manual intervention needed
6. Verify dependencies
7. Show success message with next steps

### macOS-Specific Considerations
- Default shell changed to zsh in Catalina (10.15+)
- Users may still use bash via `/bin/bash`
- Completion paths differ:
  - Bash: `~/.bash_profile` or `~/.bashrc`
  - Zsh: `~/.zshrc`
- May need to convert bash completion to zsh format

### Error Handling
- Permissions issues writing to home directory
- RC file locked or in use
- Missing dependencies can't be installed
- Provide clear error messages and manual fix instructions

## Related Files
- `xts-completion.bash`: Current bash completion script
- `TAB_COMPLETION.md`: Documentation for manual installation
- `src/xts_core/install.py`: New module for install command (to be created)

## Testing Requirements
- Test on Linux (various distros)
- Test on macOS (bash and zsh)
- Test with existing installations
- Test with missing directories
- Test permission scenarios

## Future Enhancements
- `xts uninstall`: Remove XTS installation
- `xts update`: Update completion scripts and dependencies
- Support for fish shell
- System-wide installation option (`/etc/bash_completion.d/`)
