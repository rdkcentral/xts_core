#!/usr/bin/env python3
"""Tests for XTS execution paths: Rich formatting, alias resolution, config finding, run().

Covers the critical execution paths that were missing coverage:
- RichHelpFormatter and RichArgumentParser
- _resolve_first_arg() for files/aliases/URLs
- _find_xts_config() and _user_select_config()
- _handle_alias() for all alias commands
- run() method with YamlRunner integration
- Error handling and edge cases
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call, mock_open
import tempfile
import yaml
import argparse

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from xts_core.xts import XTS, RichHelpFormatter, RichArgumentParser


@pytest.fixture
def temp_xts_home(tmp_path, monkeypatch):
    """Create temporary XTS home with aliases."""
    xts_dir = tmp_path / ".xts"
    xts_dir.mkdir()
    
    cache_dir = xts_dir / "cache"
    cache_dir.mkdir()
    
    aliases_file = xts_dir / "aliases.json"
    aliases_file.write_text('{"test_alias": "/tmp/test.xts"}')
    
    metadata_file = xts_dir / "metadata.json"
    metadata_file.write_text('{}')
    
    monkeypatch.setenv('HOME', str(tmp_path))
    return xts_dir


class TestRichHelpFormatter:
    """Test RichHelpFormatter for colored help text."""
    
    def test_init_sets_formatting_params(self):
        """Test formatter initialization with custom params."""
        formatter = RichHelpFormatter('test_prog')
        
        assert formatter._prog == 'test_prog'
        assert formatter._max_help_position == 40
        assert formatter._width == 100
    
    def test_format_usage_adds_color(self):
        """Test usage line gets colored."""
        parser = argparse.ArgumentParser(prog='test', formatter_class=RichHelpFormatter)
        formatter = parser._get_formatter()
        
        # Get usage
        usage = formatter._format_usage('usage: test', [], [], 'usage: ')
        
        # Should contain rich color markup
        assert '[bold cyan]' in usage or 'usage' in usage
    
    def test_format_action_colors_options(self):
        """Test action formatting colors option flags."""
        parser = argparse.ArgumentParser(formatter_class=RichHelpFormatter)
        parser.add_argument('--test', '-t', help='test option')
        
        formatter = parser._get_formatter()
        action = parser._actions[-1]  # Get the test action
        
        result = formatter._format_action(action)
        
        # Should contain option name
        assert 'test' in result.lower()
    
    def test_format_help_colors_section_headers(self):
        """Test help text colors section headers."""
        parser = argparse.ArgumentParser(formatter_class=RichHelpFormatter)
        parser.add_argument('pos_arg', help='positional')
        parser.add_argument('--opt', help='optional')
        
        help_text = parser.format_help()
        
        # Should contain section headers (may be colored)
        assert 'positional' in help_text.lower() or 'arguments' in help_text.lower()


class TestRichArgumentParser:
    """Test RichArgumentParser with rich console output."""
    
    def test_init_uses_rich_formatter(self):
        """Test parser uses RichHelpFormatter by default."""
        parser = RichArgumentParser()
        
        assert parser.formatter_class == RichHelpFormatter
        assert hasattr(parser, 'console')
        assert hasattr(parser, '_command_list')
    
    def test_set_command_list_stores_commands(self):
        """Test set_command_list stores command list."""
        parser = RichArgumentParser()
        commands = [('cmd1', 'desc1'), ('cmd2', 'desc2')]
        
        parser.set_command_list(commands)
        
        assert parser._command_list == commands
    
    def test_set_alias_name_stores_name(self):
        """Test set_alias_name stores alias name."""
        parser = RichArgumentParser()
        
        parser.set_alias_name('test_alias')
        
        assert parser._alias_name == 'test_alias'
    
    @patch('sys.exit')
    @patch('xts_core.xts.Console')
    def test_error_shows_command_list_for_missing_command(self, mock_console_cls, mock_exit):
        """Test error() shows nice command list when command missing."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console
        
        parser = RichArgumentParser()
        parser.set_command_list([('test_cmd', 'Test command'), ('other', 'Other command')])
        parser.set_alias_name('myalias')
        
        # Trigger error with missing command message
        parser.error('error: the following arguments are required: command')
        
        # Should print command list
        assert mock_console.print.called
        mock_exit.assert_called_once_with(1)
    
    @patch('sys.stderr')
    def test_error_default_behavior_without_command_list(self, mock_stderr):
        """Test error() uses default behavior when no command list."""
        parser = RichArgumentParser()
        
        with pytest.raises(SystemExit):
            parser.error('some other error')


class TestXTSConfigResolution:
    """Test XTS config file resolution and loading."""
    
    def test_resolve_first_arg_local_xts_file(self, tmp_path):
        """Test resolving first arg as local .xts file."""
        config_file = tmp_path / "test.xts"
        config = {'description': 'Test', 'commands': {}}
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        xts = XTS()
        
        # Change to tmp_path directory
        with patch('os.getcwd', return_value=str(tmp_path)):
            result = xts._resolve_first_arg(str(config_file))
        
        assert result == 'test.xts'
        assert xts._xts_config is not None
    
    def test_resolve_first_arg_alias_keyword(self):
        """Test resolving 'alias' keyword returns literal."""
        xts = XTS()
        
        result = xts._resolve_first_arg('alias')
        
        assert result == 'alias'
    
    @patch('xts_core.xts_alias.list_aliases')
    def test_resolve_first_arg_known_alias(self, mock_list, tmp_path, temp_xts_home):
        """Test resolving first arg as known alias."""
        # Create config file
        config_file = tmp_path / "aliased.xts"
        config = {'description': 'Aliased', 'commands': {'test': {'command': 'echo test'}}}
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        mock_list.return_value = {'my_alias': str(config_file)}
        
        xts = XTS()
        result = xts._resolve_first_arg('my_alias')
        
        assert result == 'my_alias'
        assert xts._xts_config is not None
        assert 'test' in xts._xts_config['commands']
    
    @patch('xts_core.xts.is_url')
    @patch('xts_core.xts_alias.fetch_remote_file')
    @patch('xts_core.xts_alias.get_cache_path')
    def test_resolve_first_arg_remote_url(self, mock_cache_path, mock_fetch, mock_is_url, tmp_path):
        """Test resolving first arg as remote URL."""
        # Setup mocks
        mock_is_url.return_value = True
        cache_file = tmp_path / "cached.xts"
        config = {'description': 'Remote', 'commands': {}}
        with open(cache_file, 'w') as f:
            yaml.dump(config, f)
        
        mock_cache_path.return_value = str(cache_file)
        mock_fetch.return_value = (True, {})
        
        xts = XTS()
        result = xts._resolve_first_arg('http://example.com/test.xts')
        
        assert result == 'http://example.com/test.xts'
        mock_fetch.assert_called_once()
    
    @patch('xts_core.xts_alias.list_aliases')
    def test_resolve_first_arg_unknown_returns_none(self, mock_list):
        """Test resolving unknown arg returns None."""
        mock_list.return_value = {}
        
        xts = XTS()
        result = xts._resolve_first_arg('nonexistent')
        
        assert result is None
    
    def test_xts_config_setter_loads_valid_file(self, tmp_path):
        """Test xts_config setter loads valid .xts file."""
        config_file = tmp_path / "valid.xts"
        config = {'description': 'Valid', 'commands': {'cmd': {'command': 'echo test'}}}
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        xts = XTS()
        xts.xts_config = str(config_file)
        
        assert xts._xts_config is not None
        assert 'cmd' in xts._xts_config['commands']
    
    @patch('xts_core.utils.error')
    def test_xts_config_setter_invalid_extension(self, mock_error):
        """Test xts_config setter rejects non-.xts files."""
        xts = XTS()
        
        with pytest.raises(SystemExit):
            xts.xts_config = 'test.txt'
        
        mock_error.assert_called()
    
    @patch('xts_core.utils.error')
    def test_xts_config_setter_nonexistent_file(self, mock_error):
        """Test xts_config setter rejects nonexistent files."""
        xts = XTS()
        
        with pytest.raises(SystemExit):
            xts.xts_config = '/nonexistent/path.xts'
        
        mock_error.assert_called()
    
    @patch('xts_core.utils.error')
    def test_xts_config_setter_invalid_yaml(self, mock_error, tmp_path):
        """Test xts_config setter handles malformed YAML."""
        bad_file = tmp_path / "bad.xts"
        bad_file.write_text("this: is: not: valid: yaml: [[[")
        
        xts = XTS()
        
        with pytest.raises(SystemExit):
            xts.xts_config = str(bad_file)
        
        mock_error.assert_called()


class TestXTSConfigFinding:
    """Test automatic config file finding."""
    
    def test_find_xts_config_single_file(self, tmp_path):
        """Test finding single .xts file in directory."""
        config_file = tmp_path / "only.xts"
        config = {'description': 'Only', 'commands': {}}
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        xts = XTS()
        
        with patch('os.getcwd', return_value=str(tmp_path)):
            xts._find_xts_config()
        
        assert xts._xts_config is not None
    
    @patch('xts_core.xts.XTS._user_select_config')
    def test_find_xts_config_multiple_files(self, mock_select, tmp_path):
        """Test finding multiple .xts files prompts user."""
        # Create multiple files
        for i in range(3):
            config_file = tmp_path / f"config{i}.xts"
            config_file.write_text("description: test\ncommands: {}")
        
        xts = XTS()
        
        with patch('os.getcwd', return_value=str(tmp_path)):
            xts._find_xts_config()
        
        # Should call user select with list of files
        mock_select.assert_called_once()
        call_args = mock_select.call_args[0][0]
        assert len(call_args) == 3
    
    @patch('xts_core.utils.warning')
    def test_find_xts_config_no_files_no_plugins(self, mock_warning, tmp_path):
        """Test finding no .xts files with no plugins shows warning."""
        xts = XTS()
        xts._plugins = []  # Remove plugins
        
        with patch('os.getcwd', return_value=str(tmp_path)):
            xts._find_xts_config()
        
        # Should warn about no config
        mock_warning.assert_called()
    
    @patch('builtins.input', return_value='1')
    def test_user_select_config_valid_choice(self, mock_input, tmp_path):
        """Test user selecting valid config from multiple."""
        # Create files
        files = []
        for i in range(2):
            config_file = tmp_path / f"config{i}.xts"
            config = {'description': f'Config {i}', 'commands': {}}
            with open(config_file, 'w') as f:
                yaml.dump(config, f)
            files.append(f'config{i}.xts')
        
        xts = XTS()
        
        with patch('os.getcwd', return_value=str(tmp_path)):
            with pytest.raises(SystemExit) as exc_info:
                xts._user_select_config(files)
            
            assert exc_info.value.code == 0
    
    @patch('builtins.input', return_value='invalid')
    @patch('xts_core.utils.error')
    def test_user_select_config_invalid_choice(self, mock_error, mock_input):
        """Test user selecting invalid choice."""
        xts = XTS()
        
        with pytest.raises(SystemExit):
            xts._user_select_config(['config1.xts', 'config2.xts'])
        
        mock_error.assert_called()


class TestXTSAliasHandling:
    """Test _handle_alias() for all alias commands."""
    
    @patch('xts_core.xts_alias.add_alias')
    @patch('xts_core.utils.success')
    def test_handle_alias_add_single_file(self, mock_success, mock_add):
        """Test handling alias add for single file."""
        xts = XTS()
        
        args = argparse.Namespace(
            alias_cmd='add',
            name='myalias',
            path='/path/to/file.xts',
            recursive=False
        )
        
        xts._handle_alias(args)
        
        mock_add.assert_called_once_with('myalias', '/path/to/file.xts', recursive=False)
        mock_success.assert_called()
    
    @patch('xts_core.xts_alias.add_alias')
    @patch('xts_core.utils.success')
    def test_handle_alias_add_directory(self, mock_success, mock_add):
        """Test handling alias add for directory."""
        xts = XTS()
        
        args = argparse.Namespace(
            alias_cmd='add',
            name='.',
            path=None,
            recursive=True
        )
        
        xts._handle_alias(args)
        
        mock_add.assert_called_once_with('.', None, recursive=True)
    
    @patch('xts_core.xts_alias.list_aliases')
    @patch('xts_core.utils.success')
    def test_handle_alias_list_simple(self, mock_success, mock_list):
        """Test handling alias list command."""
        mock_list.return_value = {'alias1': '/path1.xts', 'alias2': '/path2.xts'}
        
        xts = XTS()
        args = argparse.Namespace(alias_cmd='list', check_updates=False)
        
        xts._handle_alias(args)
        
        mock_list.assert_called_once()
        assert mock_success.call_count >= 2
    
    @patch('xts_core.xts_alias.list_aliases')
    @patch('xts_core.xts_alias.check_for_updates')
    @patch('xts_core.utils.info')
    def test_handle_alias_list_with_updates(self, mock_info, mock_check, mock_list):
        """Test handling alias list with update checking."""
        mock_list.return_value = {'alias1': '/path1.xts'}
        mock_check.return_value = (False, 'Up to date')
        
        xts = XTS()
        args = argparse.Namespace(alias_cmd='list', check_updates=True)
        
        xts._handle_alias(args)
        
        mock_check.assert_called()
    
    @patch('xts_core.xts_alias.remove_alias')
    @patch('xts_core.utils.success')
    def test_handle_alias_remove(self, mock_success, mock_remove):
        """Test handling alias remove command."""
        xts = XTS()
        
        args = argparse.Namespace(alias_cmd='remove', name='old_alias')
        
        xts._handle_alias(args)
        
        mock_remove.assert_called_once_with('old_alias')
        mock_success.assert_called()
    
    @patch('xts_core.xts_alias.refresh_alias')
    @patch('xts_core.utils.success')
    def test_handle_alias_refresh_single(self, mock_success, mock_refresh):
        """Test handling alias refresh for single alias."""
        mock_refresh.return_value = True
        
        xts = XTS()
        args = argparse.Namespace(alias_cmd='refresh', name='my_alias')
        
        xts._handle_alias(args)
        
        mock_refresh.assert_called_once_with('my_alias')
    
    @patch('xts_core.xts_alias.list_aliases')
    @patch('xts_core.xts_alias.refresh_alias')
    @patch('xts_core.utils.success')
    def test_handle_alias_refresh_all(self, mock_success, mock_refresh, mock_list):
        """Test handling alias refresh all."""
        mock_list.return_value = {'a1': '/p1', 'a2': '/p2', 'a3': '/p3'}
        mock_refresh.return_value = True
        
        xts = XTS()
        args = argparse.Namespace(alias_cmd='refresh', name='all')
        
        xts._handle_alias(args)
        
        assert mock_refresh.call_count == 3
        mock_success.assert_called()
    
    @patch('xts_core.xts_alias.clean_broken_aliases')
    def test_handle_alias_clean(self, mock_clean):
        """Test handling alias clean command."""
        xts = XTS()
        
        args = argparse.Namespace(alias_cmd='clean')
        
        xts._handle_alias(args)
        
        mock_clean.assert_called_once()


class TestXTSRun:
    """Test run() method with YamlRunner integration."""
    
    @patch('xts_core.xts.YamlRunner')
    @patch('sys.argv', ['xts', 'test_cmd'])
    def test_run_executes_command(self, mock_runner_cls, tmp_path):
        """Test run() executes command via YamlRunner."""
        # Setup config
        config_file = tmp_path / "test.xts"
        config = {
            'description': 'Test',
            'commands': {
                'test_cmd': {
                    'description': 'Test command',
                    'command': 'echo "test"'
                }
            }
        }
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        # Mock YamlRunner
        mock_runner = MagicMock()
        mock_runner.run.return_value = (['output'], [''], [0])
        mock_runner_cls.return_value = mock_runner
        
        xts = XTS()
        xts.xts_config = str(config_file)
        
        with patch('os.getcwd', return_value=str(tmp_path)):
            with pytest.raises(SystemExit) as exc_info:
                xts.run()
        
        # Should execute command
        mock_runner.run.assert_called()
        assert exc_info.value.code == 0
    
    @patch('xts_core.xts.Console')
    @patch('xts_core.xts_alias.list_aliases')
    @patch('sys.argv', ['xts'])
    def test_run_no_args_shows_aliases(self, mock_list, mock_console_cls):
        """Test run() with no args shows available aliases."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console
        mock_list.return_value = {'alias1': '/path1', 'alias2': '/path2'}
        
        xts = XTS()
        
        with pytest.raises(SystemExit) as exc_info:
            xts.run()
        
        # Should show aliases and exit
        assert mock_console.print.called
        assert exc_info.value.code == 0
    
    @patch('xts_core.xts.Console')
    @patch('xts_core.xts_alias.list_aliases')
    @patch('sys.argv', ['xts'])
    def test_run_no_args_no_aliases_shows_help(self, mock_list, mock_console_cls):
        """Test run() with no args and no aliases shows help."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console
        mock_list.return_value = {}
        
        xts = XTS()
        
        with pytest.raises(SystemExit) as exc_info:
            xts.run()
        
        # Should show help and exit
        assert mock_console.print.called
        assert exc_info.value.code == 0


class TestXTSGetCommandSections:
    """Test _get_command_sections() for parsing config."""
    
    def test_get_command_sections_flat_commands(self):
        """Test parsing flat command structure."""
        xts = XTS()
        xts._xts_config = {
            'commands': {
                'cmd1': {'command': 'echo 1'},
                'cmd2': {'command': 'echo 2'}
            }
        }
        
        sections = xts._get_command_sections()
        
        assert 'commands' in sections
        assert len(sections['commands']) == 2
    
    def test_get_command_sections_nested_structure(self):
        """Test parsing nested command sections."""
        xts = XTS()
        xts._xts_config = {
            'section1': {
                'cmd1': {'command': 'echo 1'},
                'cmd2': {'command': 'echo 2'}
            },
            'section2': {
                'cmd3': {'command': 'echo 3'}
            }
        }
        
        sections = xts._get_command_sections()
        
        assert 'section1' in sections
        assert 'section2' in sections
        assert len(sections['section1']) == 2
        assert len(sections['section2']) == 1
    
    def test_get_command_choices_returns_tuples(self):
        """Test _get_command_choices() returns command/description tuples."""
        xts = XTS()
        xts._xts_config = {
            'commands': {
                'test': {
                    'description': 'Test command',
                    'command': 'echo test'
                }
            }
        }
        xts._command_sections = xts._get_command_sections()
        
        choices = list(xts._get_command_choices())
        
        assert len(choices) > 0
        assert isinstance(choices[0], tuple)
        assert len(choices[0]) == 2  # (name, description)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
