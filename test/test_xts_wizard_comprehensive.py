#!/usr/bin/env python3
"""Comprehensive tests for xts_wizard.py to achieve 70%+ coverage.

Tests the interactive command creation, editing, deletion, validation,
and full workflow execution paths that were previously untested.
"""

import os
import sys
import json
import pytest
import signal
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call, mock_open
import yaml

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from xts_core.xts_wizard import XTSWizard, WizardState


class TestWizardRun:
    """Test XTSWizard.run() method and workflow execution."""
    
    @patch('builtins.input', side_effect=[
        'test_cmd',           # command name
        'Test description',   # description
        'echo "hello"',       # command
        'n',                  # add arguments?
        'n'                   # add another command?
    ])
    def test_run_create_workflow_success(self, mock_input, tmp_path):
        """Test successful create workflow execution."""
        filepath = str(tmp_path / "test.xts")
        wizard = XTSWizard(filepath, edit_mode=False)
        
        # Mock validator to return success
        with patch.object(wizard.validator, 'validate_file', return_value=(True, [], [])):
            result = wizard.run(resume=False)
        
        # Should complete successfully
        assert result == 0
        assert Path(filepath).exists()
    
    @patch('builtins.input', side_effect=[
        'test_cmd',           # command name
        'Test description',   # description
        'invalid_command',    # invalid command
        'n',                  # add arguments?
        'n',                  # add another command?
        'n'                   # save progress?
    ])
    def test_run_create_workflow_validation_fails(self, mock_input, tmp_path):
        """Test create workflow with validation failure."""
        filepath = str(tmp_path / "test.xts")
        wizard = XTSWizard(filepath, edit_mode=False)
        
        # Mock validator to return errors - error() will call sys.exit()
        with patch.object(wizard.validator, 'validate_file', return_value=(False, ['Error 1'], [])):
            with pytest.raises(SystemExit) as exc_info:
                wizard.run(resume=False)
        
        # Should exit with code 1
        assert exc_info.value.code == 1
    
    def test_run_edit_mode_file_not_found(self, tmp_path):
        """Test edit mode with missing file."""
        filepath = str(tmp_path / "missing.xts")
        wizard = XTSWizard(filepath, edit_mode=True)
        
        # Should raise SystemExit when file doesn't exist
        with pytest.raises(SystemExit) as exc_info:
            wizard.run(resume=False)
        
        assert exc_info.value.code == 1
    
    def test_run_edit_mode_success(self, tmp_path):
        """Test edit mode with existing file."""
        # Create existing file
        filepath = tmp_path / "existing.xts"
        config = {
            'description': 'Existing',
            'commands': {
                'test': {
                    'description': 'Test',
                    'command': 'echo "test"'
                }
            }
        }
        with open(filepath, 'w') as f:
            yaml.dump(config, f)
        
        filepath_str = str(filepath)
        wizard = XTSWizard(filepath_str, edit_mode=True)
        
        # Mock input to exit edit menu immediately
        with patch('builtins.input', return_value='4'):  # Option 4 = Done editing
            with patch.object(wizard.validator, 'validate_file', return_value=(True, [], [])):
                result = wizard.run(resume=False)
        
        assert result == 0
    
    def test_run_resume_mode_no_state(self, tmp_path):
        """Test resume mode when no saved state exists."""
        filepath = str(tmp_path / "test.xts")
        wizard = XTSWizard(filepath, edit_mode=False)
        
        # Should raise SystemExit when no state file exists
        with pytest.raises(SystemExit) as exc_info:
            wizard.run(resume=True)
        
        assert exc_info.value.code == 1


class TestAddCommand:
    """Test _add_command() method."""
    
    @patch('builtins.input', side_effect=[
        'build',                # command name
        'Build the project',    # description
        'make all',             # command
        'n'                     # add arguments?
    ])
    def test_add_command_minimal(self, mock_input, tmp_path):
        """Test adding minimal command."""
        filepath = str(tmp_path / "test.xts")
        wizard = XTSWizard(filepath)
        
        wizard._add_command()
        
        assert 'build' in wizard.state.config['commands']
        assert wizard.state.config['commands']['build']['command'] == 'make all'
        assert wizard.state.config['commands']['build']['description'] == 'Build the project'
    
    @patch('builtins.input', side_effect=[
        '',                     # empty name (invalid)
        'build-test',           # invalid name with dash
        'build_test',           # valid name
        'Build and test',       # description
        'make test',            # command
        'y',                    # add arguments? yes
        'target',               # arg name
        'Build target',         # arg description
        'y',                    # required? yes
        'n'                     # add another arg? no
    ])
    def test_add_command_with_args(self, mock_input, tmp_path):
        """Test adding command with arguments."""
        filepath = str(tmp_path / "test.xts")
        wizard = XTSWizard(filepath)
        
        wizard._add_command()
        
        cmd = wizard.state.config['commands']['build_test']
        assert cmd['command'] == 'make test'
        assert len(cmd['args']) == 1
        assert cmd['args'][0]['name'] == 'target'
        assert cmd['args'][0]['required'] is True
    
    @patch('builtins.input', side_effect=[
        'test',                 # first command
        'Test',                 # description
        'echo "test"',          # command
        'n',                    # add arguments?
        'test',                 # try to add duplicate
        'test2',                # valid unique name
        'Test 2',               # description
        'echo "test2"',         # command
        'n'                     # add arguments?
    ])
    def test_add_command_duplicate_name_rejected(self, mock_input, tmp_path):
        """Test that duplicate command names are rejected."""
        filepath = str(tmp_path / "test.xts")
        wizard = XTSWizard(filepath)
        
        # Add first command
        wizard._add_command()
        assert 'test' in wizard.state.config['commands']
        
        # Try to add duplicate (should ask again and accept test2)
        wizard._add_command()
        assert 'test2' in wizard.state.config['commands']
        assert len(wizard.state.config['commands']) == 2


class TestPromptForArg:
    """Test _prompt_for_arg() method."""
    
    @patch('builtins.input', side_effect=[
        'url',                  # arg name
        'URL to fetch',         # description
        'y'                     # required? yes
    ])
    def test_prompt_for_arg_required(self, mock_input, tmp_path):
        """Test prompting for required argument."""
        filepath = str(tmp_path / "test.xts")
        wizard = XTSWizard(filepath)
        
        arg = wizard._prompt_for_arg()
        
        assert arg is not None
        assert arg['name'] == 'url'
        assert arg['description'] == 'URL to fetch'
        assert arg['required'] is True
        assert 'default' not in arg
    
    @patch('builtins.input', side_effect=[
        'port',                 # arg name
        'Port number',          # description
        'n',                    # required? no
        '8080'                  # default value
    ])
    def test_prompt_for_arg_optional_with_default(self, mock_input, tmp_path):
        """Test prompting for optional argument with default."""
        filepath = str(tmp_path / "test.xts")
        wizard = XTSWizard(filepath)
        
        arg = wizard._prompt_for_arg()
        
        assert arg is not None
        assert arg['name'] == 'port'
        assert arg['required'] is False
        assert arg['default'] == '8080'
    
    @patch('builtins.input', side_effect=[
        '',                     # empty arg name
    ])
    def test_prompt_for_arg_empty_name_returns_none(self, mock_input, tmp_path):
        """Test that empty argument name returns None."""
        filepath = str(tmp_path / "test.xts")
        wizard = XTSWizard(filepath)
        
        arg = wizard._prompt_for_arg()
        
        assert arg is None


class TestEditCommand:
    """Test _edit_command() method."""
    
    def test_edit_command_no_commands(self, tmp_path):
        """Test editing when no commands exist."""
        filepath = str(tmp_path / "test.xts")
        wizard = XTSWizard(filepath)
        
        # No commands exist
        wizard._edit_command()
        
        # Should return without error
        assert True
    
    @patch('builtins.input', side_effect=[
        'test_cmd',             # command to edit
        'Updated description',  # new description
        'echo "updated"'        # new command
    ])
    def test_edit_command_success(self, mock_input, tmp_path):
        """Test editing command successfully."""
        filepath = str(tmp_path / "test.xts")
        wizard = XTSWizard(filepath)
        
        # Add initial command
        wizard.state.config['commands'] = {
            'test_cmd': {
                'description': 'Old description',
                'command': 'echo "old"'
            }
        }
        
        wizard._edit_command()
        
        cmd = wizard.state.config['commands']['test_cmd']
        assert cmd['description'] == 'Updated description'
        assert cmd['command'] == 'echo "updated"'
    
    @patch('builtins.input', side_effect=[
        'nonexistent'           # command that doesn't exist
    ])
    def test_edit_command_not_found(self, mock_input, tmp_path):
        """Test editing non-existent command."""
        filepath = str(tmp_path / "test.xts")
        wizard = XTSWizard(filepath)
        
        wizard.state.config['commands'] = {
            'test_cmd': {
                'description': 'Test',
                'command': 'echo "test"'
            }
        }
        
        wizard._edit_command()
        
        # Should return without modifying
        assert wizard.state.config['commands']['test_cmd']['description'] == 'Test'
    
    @patch('builtins.input', side_effect=[
        'test_cmd',             # command to edit
        '',                     # keep description
        ''                      # keep command
    ])
    def test_edit_command_keep_existing_values(self, mock_input, tmp_path):
        """Test editing command with empty inputs keeps existing values."""
        filepath = str(tmp_path / "test.xts")
        wizard = XTSWizard(filepath)
        
        wizard.state.config['commands'] = {
            'test_cmd': {
                'description': 'Original description',
                'command': 'echo "original"'
            }
        }
        
        wizard._edit_command()
        
        cmd = wizard.state.config['commands']['test_cmd']
        assert cmd['description'] == 'Original description'
        assert cmd['command'] == 'echo "original"'


class TestDeleteCommand:
    """Test _delete_command() method."""
    
    def test_delete_command_no_commands(self, tmp_path):
        """Test deleting when no commands exist."""
        filepath = str(tmp_path / "test.xts")
        wizard = XTSWizard(filepath)
        
        wizard._delete_command()
        
        # Should return without error
        assert True
    
    @patch('builtins.input', side_effect=[
        'test_cmd',             # command to delete
        'y'                     # confirm deletion
    ])
    def test_delete_command_success(self, mock_input, tmp_path):
        """Test deleting command successfully."""
        filepath = str(tmp_path / "test.xts")
        wizard = XTSWizard(filepath)
        
        wizard.state.config['commands'] = {
            'test_cmd': {
                'description': 'Test',
                'command': 'echo "test"'
            },
            'other_cmd': {
                'description': 'Other',
                'command': 'echo "other"'
            }
        }
        
        wizard._delete_command()
        
        assert 'test_cmd' not in wizard.state.config['commands']
        assert 'other_cmd' in wizard.state.config['commands']
    
    @patch('builtins.input', side_effect=[
        'test_cmd',             # command to delete
        'n'                     # cancel deletion
    ])
    def test_delete_command_cancelled(self, mock_input, tmp_path):
        """Test cancelling command deletion."""
        filepath = str(tmp_path / "test.xts")
        wizard = XTSWizard(filepath)
        
        wizard.state.config['commands'] = {
            'test_cmd': {
                'description': 'Test',
                'command': 'echo "test"'
            }
        }
        
        wizard._delete_command()
        
        # Should still exist
        assert 'test_cmd' in wizard.state.config['commands']
    
    @patch('builtins.input', return_value='nonexistent')
    def test_delete_command_not_found(self, mock_input, tmp_path):
        """Test deleting non-existent command."""
        filepath = str(tmp_path / "test.xts")
        wizard = XTSWizard(filepath)
        
        wizard.state.config['commands'] = {
            'test_cmd': {
                'description': 'Test',
                'command': 'echo "test"'
            }
        }
        
        wizard._delete_command()
        
        # Should return without modifying
        assert 'test_cmd' in wizard.state.config['commands']


class TestValidateConfig:
    """Test _validate_config() method."""
    
    def test_validate_config_success(self, tmp_path):
        """Test validating valid configuration."""
        filepath = str(tmp_path / "test.xts")
        wizard = XTSWizard(filepath)
        
        wizard.state.config = {
            'description': 'Test config',
            'commands': {
                'test': {
                    'description': 'Test',
                    'command': 'echo "test"'
                }
            }
        }
        
        with patch.object(wizard.validator, 'validate_file', return_value=(True, [], [])):
            result = wizard._validate_config()
        
        assert result is True
    
    def test_validate_config_with_errors(self, tmp_path):
        """Test validating invalid configuration."""
        filepath = str(tmp_path / "test.xts")
        wizard = XTSWizard(filepath)
        
        wizard.state.config = {
            'commands': {
                'bad_cmd': {
                    'description': 'Missing command field'
                }
            }
        }
        
        # error() will call sys.exit() when validation fails
        with patch.object(wizard.validator, 'validate_file', return_value=(False, ['Error 1'], [])):
            with pytest.raises(SystemExit) as exc_info:
                wizard._validate_config()
        
        assert exc_info.value.code == 1
    
    def test_validate_config_with_warnings(self, tmp_path):
        """Test validating configuration with warnings."""
        filepath = str(tmp_path / "test.xts")
        wizard = XTSWizard(filepath)
        
        wizard.state.config = {
            'commands': {
                'test': {
                    'description': 'Test',
                    'command': 'echo "test"'
                }
            }
        }
        
        with patch.object(wizard.validator, 'validate_file', return_value=(True, [], ['Warning 1'])):
            result = wizard._validate_config()
        
        assert result is True


class TestWriteConfig:
    """Test _write_config() method."""
    
    def test_write_config_creates_file(self, tmp_path):
        """Test that _write_config() creates file with proper format."""
        filepath = tmp_path / "output.xts"
        wizard = XTSWizard(str(filepath))
        
        wizard.state.config = {
            'description': 'Test config',
            'commands': {
                'test': {
                    'description': 'Test command',
                    'command': 'echo "test"'
                }
            }
        }
        
        wizard._write_config()
        
        assert filepath.exists()
        
        # Read and verify content
        content = filepath.read_text()
        
        # Check copyright header
        assert 'Copyright 2026 RDK Management' in content
        assert 'Apache License' in content
        
        # Check YAML content
        assert 'description: Test config' in content
        assert 'commands:' in content
        assert 'test:' in content
        assert 'echo "test"' in content
    
    def test_write_config_with_functions(self, tmp_path):
        """Test writing config with functions."""
        filepath = tmp_path / "output.xts"
        wizard = XTSWizard(str(filepath))
        
        wizard.state.config = {
            'description': 'Config with functions',
            'functions': {
                'format_output': {
                    'description': 'Format output',
                    'command': 'jq .'
                }
            },
            'commands': {
                'test': {
                    'description': 'Test',
                    'command': 'echo "test"',
                    'formatter': 'format_output'
                }
            }
        }
        
        wizard._write_config()
        
        content = filepath.read_text()
        assert 'functions:' in content
        assert 'format_output:' in content
        assert 'jq .' in content


class TestPrintHeaderAndIntro:
    """Test _print_header() and _show_intro() methods."""
    
    @patch('builtins.print')
    def test_print_header_create_mode(self, mock_print, tmp_path):
        """Test header in create mode."""
        filepath = str(tmp_path / "test.xts")
        wizard = XTSWizard(filepath, edit_mode=False)
        
        wizard._print_header()
        
        # Verify print was called with create mode
        call_args = [str(call) for call in mock_print.call_args_list]
        assert any('Create Mode' in str(call) for call in call_args)
    
    @patch('builtins.print')
    def test_print_header_edit_mode(self, mock_print, tmp_path):
        """Test header in edit mode."""
        filepath = str(tmp_path / "test.xts")
        wizard = XTSWizard(filepath, edit_mode=True)
        
        wizard._print_header()
        
        # Verify print was called with edit mode
        call_args = [str(call) for call in mock_print.call_args_list]
        assert any('Edit Mode' in str(call) for call in call_args)
    
    @patch('builtins.print')
    def test_show_intro(self, mock_print, tmp_path):
        """Test intro message."""
        filepath = str(tmp_path / "test.xts")
        wizard = XTSWizard(filepath)
        
        wizard._show_intro()
        
        # Verify intro text was printed
        call_args = [str(call) for call in mock_print.call_args_list]
        assert any('help you create' in str(call) for call in call_args)
        assert any('CTRL-C' in str(call) for call in call_args)


class TestLoadExisting:
    """Test _load_existing() method."""
    
    def test_load_existing_file_not_found(self, tmp_path):
        """Test loading when file doesn't exist."""
        filepath = tmp_path / "missing.xts"
        wizard = XTSWizard(str(filepath), edit_mode=True)
        
        # Should raise SystemExit when file doesn't exist
        with pytest.raises(SystemExit) as exc_info:
            wizard._load_existing()
        
        assert exc_info.value.code == 1
    
    def test_load_existing_success(self, tmp_path):
        """Test loading existing file successfully."""
        filepath = tmp_path / "existing.xts"
        config = {
            'description': 'Existing config',
            'commands': {
                'test': {
                    'description': 'Test',
                    'command': 'echo "test"'
                }
            }
        }
        
        with open(filepath, 'w') as f:
            yaml.dump(config, f)
        
        wizard = XTSWizard(str(filepath), edit_mode=True)
        result = wizard._load_existing()
        
        assert result is True
        assert wizard.state.config.get('description') == 'Existing config'
        assert 'test' in wizard.state.config.get('commands', {})


class TestHandleInterrupt:
    """Test _handle_interrupt() signal handler."""
    
    @patch('builtins.input', return_value='y')
    @patch('sys.exit')
    def test_handle_interrupt_save_progress(self, mock_exit, mock_input, tmp_path):
        """Test interrupt handler saves progress when user says yes."""
        filepath = str(tmp_path / "test.xts")
        wizard = XTSWizard(filepath)
        
        wizard.state.config['commands'] = {'test': {'description': 'Test', 'command': 'echo "test"'}}
        
        # Simulate CTRL-C
        wizard._handle_interrupt(signal.SIGINT, None)
        
        # Verify exit was called
        mock_exit.assert_called_once_with(0)
    
    @patch('builtins.input', return_value='n')
    @patch('sys.exit')
    def test_handle_interrupt_no_save(self, mock_exit, mock_input, tmp_path):
        """Test interrupt handler exits without saving when user says no."""
        filepath = str(tmp_path / "test.xts")
        wizard = XTSWizard(filepath)
        
        # Simulate CTRL-C
        wizard._handle_interrupt(signal.SIGINT, None)
        
        # Verify exit was called
        mock_exit.assert_called_once_with(0)


class TestCreateWorkflow:
    """Test _create_workflow() method."""
    
    @patch('builtins.input', side_effect=[
        'test_cmd',             # command name
        'Test',                 # description
        'echo "test"',          # command
        'n',                    # add arguments?
        'n'                     # add another command?
    ])
    def test_create_workflow_minimal(self, mock_input, tmp_path):
        """Test create workflow with minimal input."""
        filepath = str(tmp_path / "test.xts")
        wizard = XTSWizard(filepath)
        
        wizard._create_workflow()
        
        assert 'test_cmd' in wizard.state.config['commands']


class TestEditWorkflow:
    """Test _edit_workflow() method."""
    
    @patch('builtins.input', return_value='4')  # Option 4 = Done editing
    def test_edit_workflow_done_immediately(self, mock_input, tmp_path):
        """Test edit workflow exits immediately."""
        filepath = str(tmp_path / "test.xts")
        wizard = XTSWizard(filepath, edit_mode=True)
        
        wizard.state.config['commands'] = {
            'test': {
                'description': 'Test',
                'command': 'echo "test"'
            }
        }
        
        wizard._edit_workflow()
        
        # Should exit without error
        assert True
    
    @patch('builtins.input', side_effect=[
        '1',                    # Option 1: Add command
        'new_cmd',              # command name
        'New command',          # description
        'echo "new"',           # command
        'n',                    # add arguments?
        '4'                     # Done editing
    ])
    def test_edit_workflow_add_command(self, mock_input, tmp_path):
        """Test edit workflow adds command."""
        filepath = str(tmp_path / "test.xts")
        wizard = XTSWizard(filepath, edit_mode=True)
        
        wizard.state.config['commands'] = {}
        
        wizard._edit_workflow()
        
        assert 'new_cmd' in wizard.state.config['commands']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
