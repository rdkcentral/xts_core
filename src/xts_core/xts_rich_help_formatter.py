from argparse import _SubParsersAction, Action

from rich_argparse import RichHelpFormatter, _lazy_rich as r

from xts_core import xts_alias

class XTSRichHelpFormatter(RichHelpFormatter):
    """
    Custom formatter to display subcommands and aliases in separate sections.
    """
    all_entries = []

    @property
    def _max_name_len(self) -> int:
        if self.all_entries:
            max_name_len = max(len(name) for name, _ in self.all_entries)
            return max_name_len + self._current_indent
        return 0

    def add_arguments(self, actions):
        # Override to inject custom subparser formatting
        subcommands = []
        aliases = []
        non_subparser_actions = []
        for action in actions:
            if isinstance(action, _SubParsersAction) and action.dest == 'alias_name':
                known_aliases = list(xts_alias.load_aliases().keys())
                for choice, parser in list(action.choices.items()):
                    # The 'alias_name' subparser is a special case used to display aliases,
                    # so we skip it in the subcommands section
                    if choice == 'alias_name':
                        continue
                    choice_action = list(filter(lambda x: parser.prog == f'xts {x.dest}', action._choices_actions))[0]
                    choice_tuple = (choice, choice_action)
                    if choice in known_aliases:
                        aliases.append(choice_tuple)
                    else:
                        subcommands.append(choice_tuple)
            else:
                non_subparser_actions.append(action)
        if non_subparser_actions:
            super().add_arguments(non_subparser_actions)
        elif subcommands or aliases:
            # Suppress the enclosing "positional arguments" heading — we render our own sections
            self._current_section.heading = None
        self.all_entries = subcommands + aliases
        if subcommands:
            self._create_section('Subcommands', subcommands)
        if aliases:
            self._create_section('Aliases', aliases)

    def _create_section(self, heading:str, actions:list[tuple[str,Action]]):
        self.start_section(heading)
        self._action_max_length = max(self._action_max_length, self._max_name_len + self._current_indent)
        for action_name, action in actions:
            header = r.Text(action_name, style="argparse.args")
            header.pad_left(self._current_indent)
            help_text = r.Text(action.help, style="argparse.help") if action.help else None
            self._current_section.rich_actions.append((header, help_text))
        self.end_section()
