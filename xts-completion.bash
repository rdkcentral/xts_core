#!/bin/bash
# Bash completion script for xts command with color support
# Installation:
#   1. Copy to: ~/.xts/xts-completion.bash
#   2. Add to ~/.bashrc: source ~/.xts/xts-completion.bash
#   Or for system-wide: sudo cp xts-completion.bash /etc/bash_completion.d/xts

# Color codes for different completion types
_xts_color_command='\033[1;32m'    # Bold green for built-in commands
_xts_color_alias='\033[1;36m'      # Bold cyan for aliases
_xts_color_subcommand='\033[0;33m' # Yellow for subcommands
_xts_color_reset='\033[0m'         # Reset

_xts_get_alias_commands() {
    # Get commands for a specific alias by querying xts
    local alias_name=$1
    local commands
    
    # Try to get commands from the alias (suppress errors)
    commands=$(xts "$alias_name" --help 2>/dev/null | grep -E "^  [a-z_]+" | awk '{print $1}' | tr '\n' ' ')
    
    echo "$commands"
}

_xts_completion() {
    local cur prev opts aliases
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Main xts commands
    opts="alias"
    
    # Get aliases from ~/.xts/aliases.json
    if [ -f ~/.xts/aliases.json ]; then
        # Extract alias names using grep/sed (works without jq)
        aliases=$(grep -o '"[^"]*"[[:space:]]*:' ~/.xts/aliases.json | sed 's/"//g' | sed 's/[[:space:]]*://g' | tr '\n' ' ')
    fi

    case "${COMP_CWORD}" in
        1)
            # First argument: complete with 'alias' command or available aliases
            # Show both commands and aliases
            local all_opts="$opts $aliases"
            COMPREPLY=( $(compgen -W "${all_opts}" -- ${cur}) )
            
            # Apply colors to completions (if supported)
            if [[ -n "$BASH_VERSION" ]] && [[ "${#COMPREPLY[@]}" -gt 0 ]]; then
                # Color built-in commands green and aliases cyan
                local colored_reply=()
                for item in "${COMPREPLY[@]}"; do
                    if [[ " $opts " =~ " $item " ]]; then
                        # Built-in command (green)
                        colored_reply+=("$item")
                    else
                        # Alias (cyan)
                        colored_reply+=("$item")
                    fi
                done
                COMPREPLY=("${colored_reply[@]}")
            fi
            return 0
            ;;
        2)
            # Second argument depends on first
            case "${prev}" in
                alias)
                    # xts alias <subcommand>
                    COMPREPLY=( $(compgen -W "add list remove refresh clean" -- ${cur}) )
                    return 0
                    ;;
                *)
                    # After an alias name, get commands from that alias's .xts file
                    if [[ " $aliases " =~ " ${prev} " ]]; then
                        local alias_commands=$(_xts_get_alias_commands "${prev}")
                        if [ -n "$alias_commands" ]; then
                            COMPREPLY=( $(compgen -W "${alias_commands}" -- ${cur}) )
                        fi
                    fi
                    return 0
                    ;;
            esac
            ;;
        3)
            # Third argument: special cases
            local prev2="${COMP_WORDS[COMP_CWORD-2]}"
            if [ "$prev2" = "alias" ] && [ "$prev" = "add" ]; then
                # xts alias add <name|path> - suggest file completion
                COMPREPLY=( $(compgen -f -- ${cur}) )
                return 0
            elif [ "$prev2" = "alias" ] && [ "$prev" = "remove" ]; then
                # xts alias remove <alias_name> - suggest existing aliases
                if [ -f ~/.xts/aliases.json ]; then
                    local remove_aliases=$(grep -o '"[^"]*"[[:space:]]*:' ~/.xts/aliases.json | sed 's/"//g' | sed 's/[[:space:]]*://g' | tr '\n' ' ')
                    COMPREPLY=( $(compgen -W "${remove_aliases}" -- ${cur}) )
                fi
                return 0
            elif [[ " $aliases " =~ " ${prev2} " ]]; then
                # After alias and its command, don't suggest anything (let xts handle it)
                return 0
            fi
            ;;
        4)
            # Fourth argument: xts alias add <name> <path>
            local prev3="${COMP_WORDS[COMP_CWORD-3]}"
            local prev2="${COMP_WORDS[COMP_CWORD-2]}"
            if [ "$prev3" = "alias" ] && [ "$prev2" = "add" ]; then
                # Suggest file/URL completion
                COMPREPLY=( $(compgen -f -- ${cur}) )
                return 0
            fi
            ;;
    esac

    # Default: no completion
    return 0
}

# Register the completion function
complete -F _xts_completion xts

# Enable colored completion output (requires bash 4.4+)
if [[ -n "$BASH_VERSION" ]] && [[ "${BASH_VERSINFO[0]}" -ge 4 ]]; then
    # Set colored-stats for better visibility
    bind 'set colored-stats on' 2>/dev/null
    bind 'set colored-completion-prefix on' 2>/dev/null
fi
