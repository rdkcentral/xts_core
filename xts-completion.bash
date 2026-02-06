#!/bin/bash
# Bash completion script for xts command
# Installation:
#   1. Copy to: ~/.xts/xts-completion.bash
#   2. Add to ~/.bashrc: source ~/.xts/xts-completion.bash
#   Or for system-wide: sudo cp xts-completion.bash /etc/bash_completion.d/xts

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
        opts="$opts $aliases"
    fi

    case "${COMP_CWORD}" in
        1)
            # First argument: complete with 'alias' or available aliases
            COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
            return 0
            ;;
        2)
            # Second argument depends on first
            case "${prev}" in
                alias)
                    # xts alias <subcommand>
                    COMPREPLY=( $(compgen -W "add list remove" -- ${cur}) )
                    return 0
                    ;;
                *)
                    # After an alias name, no completion needed (handled by the loaded .xts file)
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
