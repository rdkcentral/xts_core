#!/usr/bin/env bash

function _xts_runner_completion()
{
	local IFS='
	'
	COMPREPLY=( $( env COMP_WORDS="${COMP_WORDS[*]}" \
					COMP_CWORD=$COMP_CWORD \
					_XTS_COMPLETE=complete_bash $1 ) )
	return 0
}

complete -o default -F _xts_runner_completion xts
