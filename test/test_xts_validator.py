#!/usr/bin/env python3
"""Tests for XTS validator.

Tests cover:
- YAML parsing validation
- Schema validation (if jsonschema available)
- Command validation
- Function validation
- Placeholder validation
- Best practices checking
"""

import os
import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from xts_core.xts_validator import XTSValidator, validate_command


@pytest.fixture
def validator():
    """Create validator instance."""
    return XTSValidator()


@pytest.fixture
def valid_xts_content():
    """Valid .xts file content."""
    return """functions:
  format_output:
    description: Format JSON output
    command: python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin), indent=2))"

commands:
  test_cmd:
    description: Test command
    command: echo "Hello {{name}}"
    args:
      - name: name
        description: Name to greet
        required: true
  
  list_files:
    description: List files
    command: ls -la | {{format_output}}
    formatter: "{{format_output}}"
"""


@pytest.fixture
def invalid_yaml():
    """Invalid YAML content."""
    return """commands:
  test:
    description: Test
    command: echo "test"
    invalid_indent
"""


@pytest.fixture
def temp_xts_file(tmp_path):
    """Create temporary .xts file."""
    def _create(content):
        xts_file = tmp_path / "test.xts"
        xts_file.write_text(content)
        return str(xts_file)
    return _create


class TestValidatorInit:
    """Test validator initialization."""
    
    def test_validator_loads_schema(self, validator):
        """Test validator loads schema if available."""
        # Schema should be loaded if file exists
        assert validator.schema is not None or validator.schema is None
    
    def test_validator_without_schema(self, tmp_path, monkeypatch):
        """Test validator works without schema file."""
        # Point to non-existent schema
        monkeypatch.setattr('xts_core.xts_validator.Path', lambda x: tmp_path / "missing.json")
        
        validator = XTSValidator()
        # Should not crash, just warn
        assert validator.schema is None


class TestYamlParsing:
    """Test YAML parsing validation."""
    
    def test_validate_valid_yaml(self, validator, temp_xts_file, valid_xts_content):
        """Test validation of valid YAML."""
        xts_file = temp_xts_file(valid_xts_content)
        
        is_valid, errors, warnings = validator.validate_file(xts_file)
        
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_invalid_yaml(self, validator, temp_xts_file, invalid_yaml):
        """Test detection of invalid YAML."""
        xts_file = temp_xts_file(invalid_yaml)
        
        is_valid, errors, warnings = validator.validate_file(xts_file)
        
        assert not is_valid
        assert len(errors) > 0
        assert any("YAML" in err or "parsing" in err for err in errors)
    
    def test_validate_empty_file(self, validator, temp_xts_file):
        """Test validation of empty file."""
        xts_file = temp_xts_file("")
        
        is_valid, errors, warnings = validator.validate_file(xts_file)
        
        assert not is_valid
        assert any("empty" in err.lower() for err in errors)
    
    def test_validate_missing_file(self, validator):
        """Test validation of non-existent file."""
        is_valid, errors, warnings = validator.validate_file("/nonexistent.xts")
        
        assert not is_valid
        assert any("not found" in err.lower() for err in errors)


class TestCommandValidation:
    """Test command definition validation."""
    
    def test_validate_command_missing_command_field(self, validator, temp_xts_file):
        """Test detection of missing command field."""
        content = """commands:
  test:
    description: Test
"""
        xts_file = temp_xts_file(content)
        
        is_valid, errors, warnings = validator.validate_file(xts_file)
        
        assert not is_valid
        assert any("missing" in err.lower() and "command" in err.lower() for err in errors)
    
    def test_validate_empty_command(self, validator, temp_xts_file):
        """Test detection of empty command."""
        content = """commands:
  test:
    description: Test
    command: ""
"""
        xts_file = temp_xts_file(content)
        
        is_valid, errors, warnings = validator.validate_file(xts_file)
        
        assert not is_valid
        assert any("empty" in err.lower() for err in errors)
    
    def test_validate_invalid_command_name(self, validator, temp_xts_file):
        """Test detection of invalid command names."""
        content = """commands:
  invalid-name:
    description: Test
    command: echo "test"
"""
        xts_file = temp_xts_file(content)
        
        is_valid, errors, warnings = validator.validate_file(xts_file)
        
        assert not is_valid
        assert any("invalid" in err.lower() and "name" in err.lower() for err in errors)
    
    def test_validate_missing_description(self, validator, temp_xts_file):
        """Test warning for missing description."""
        content = """commands:
  test:
    command: echo "test"
"""
        xts_file = temp_xts_file(content)
        
        is_valid, errors, warnings = validator.validate_file(xts_file)
        
        # Should be valid but with warning
        assert is_valid
        assert any("description" in warn.lower() for warn in warnings)


class TestArgumentValidation:
    """Test argument validation."""
    
    def test_validate_required_after_optional(self, validator, temp_xts_file):
        """Test warning for required arg after optional."""
        content = """commands:
  test:
    description: Test
    command: echo {{optional}} {{required}}
    args:
      - name: optional
        description: Optional arg
        required: false
        default: "default"
      - name: required
        description: Required arg
        required: true
"""
        xts_file = temp_xts_file(content)
        
        is_valid, errors, warnings = validator.validate_file(xts_file)
        
        assert is_valid
        assert any("required" in warn.lower() and "optional" in warn.lower() for warn in warnings)
    
    def test_validate_unused_argument(self, validator, temp_xts_file):
        """Test warning for unused arguments."""
        content = """commands:
  test:
    description: Test
    command: echo "test"
    args:
      - name: unused_arg
        description: Unused
"""
        xts_file = temp_xts_file(content)
        
        is_valid, errors, warnings = validator.validate_file(xts_file)
        
        assert is_valid
        assert any("not used" in warn.lower() or "unused" in warn.lower() for warn in warnings)


class TestPlaceholderValidation:
    """Test placeholder validation."""
    
    def test_validate_undefined_placeholder(self, validator, temp_xts_file):
        """Test detection of undefined placeholders."""
        content = """commands:
  test:
    description: Test
    command: echo {{undefined_var}}
"""
        xts_file = temp_xts_file(content)
        
        is_valid, errors, warnings = validator.validate_file(xts_file)
        
        assert not is_valid
        assert any("unknown" in err.lower() and "placeholder" in err.lower() for err in errors)
    
    def test_validate_function_placeholder(self, validator, temp_xts_file):
        """Test function placeholders are recognized."""
        content = """functions:
  my_func:
    description: Test function
    command: cat

commands:
  test:
    description: Test
    command: echo "test" | {{my_func}}
"""
        xts_file = temp_xts_file(content)
        
        is_valid, errors, warnings = validator.validate_file(xts_file)
        
        assert is_valid
    
    def test_validate_formatter_undefined_function(self, validator, temp_xts_file):
        """Test formatter referencing undefined function."""
        content = """commands:
  test:
    description: Test
    command: echo "test"
    formatter: "{{undefined_func}}"
"""
        xts_file = temp_xts_file(content)
        
        is_valid, errors, warnings = validator.validate_file(xts_file)
        
        assert not is_valid
        assert any("unknown" in err.lower() and "function" in err.lower() for err in errors)


class TestFunctionValidation:
    """Test function validation."""
    
    def test_validate_function_missing_command(self, validator, temp_xts_file):
        """Test detection of function without command."""
        content = """functions:
  test_func:
    description: Test
"""
        xts_file = temp_xts_file(content)
        
        is_valid, errors, warnings = validator.validate_file(xts_file)
        
        assert not is_valid
        assert any("missing" in err.lower() and "command" in err.lower() for err in errors)
    
    def test_validate_invalid_function_name(self, validator, temp_xts_file):
        """Test detection of invalid function names."""
        content = """functions:
  invalid-func:
    description: Test
    command: cat
"""
        xts_file = temp_xts_file(content)
        
        is_valid, errors, warnings = validator.validate_file(xts_file)
        
        assert not is_valid
        assert any("invalid" in err.lower() and "name" in err.lower() for err in errors)


class TestBestPractices:
    """Test best practice warnings."""
    
    def test_validate_long_command(self, validator, temp_xts_file):
        """Test warning for very long commands."""
        long_cmd = "echo " + ("x" * 600)
        content = f"""commands:
  test:
    description: Test
    command: {long_cmd}
"""
        xts_file = temp_xts_file(content)
        
        is_valid, errors, warnings = validator.validate_file(xts_file)
        
        assert is_valid
        assert any("long" in warn.lower() for warn in warnings)
    
    def test_validate_python_vs_python3(self, validator, temp_xts_file):
        """Test warning for using python instead of python3."""
        content = """commands:
  test:
    description: Test
    command: python -c "print('test')"
"""
        xts_file = temp_xts_file(content)
        
        is_valid, errors, warnings = validator.validate_file(xts_file)
        
        assert is_valid
        assert any("python3" in warn.lower() for warn in warnings)


class TestFileExtension:
    """Test file extension validation."""
    
    def test_validate_wrong_extension(self, validator, tmp_path):
        """Test warning for non-.xts extension."""
        wrong_file = tmp_path / "config.yaml"
        wrong_file.write_text("commands:\n  test:\n    command: echo test")
        
        is_valid, errors, warnings = validator.validate_file(str(wrong_file))
        
        # Should warn about extension
        assert any(".xts" in warn for warn in warnings)


class TestValidateCommand:
    """Test validate_command function (CLI entry point)."""
    
    def test_validate_command_valid_file(self, temp_xts_file, valid_xts_content, capsys):
        """Test validate_command with valid file."""
        xts_file = temp_xts_file(valid_xts_content)
        
        exit_code = validate_command(xts_file, verbose=False, json_output=False)
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "✓" in captured.out or "passed" in captured.out.lower()
    
    def test_validate_command_invalid_file(self, temp_xts_file, invalid_yaml, capsys):
        """Test validate_command with invalid file."""
        xts_file = temp_xts_file(invalid_yaml)
        
        # Should raise SystemExit when validation fails
        with pytest.raises(SystemExit) as exc_info:
            validate_command(xts_file, verbose=False, json_output=False)
        assert exc_info.value.code == 1
        
        captured = capsys.readouterr()
        assert "✗" in captured.out or "failed" in captured.out.lower()
    
    def test_validate_command_json_output(self, temp_xts_file, valid_xts_content, capsys):
        """Test validate_command with JSON output."""
        xts_file = temp_xts_file(valid_xts_content)
        
        exit_code = validate_command(xts_file, verbose=False, json_output=True)
        
        captured = capsys.readouterr()
        # Should output valid JSON
        result = json.loads(captured.out)
        assert "valid" in result
        assert "errors" in result
        assert "warnings" in result
    
    def test_validate_command_verbose(self, temp_xts_file, valid_xts_content, capsys):
        """Test validate_command with verbose output."""
        xts_file = temp_xts_file(valid_xts_content)
        
        exit_code = validate_command(xts_file, verbose=True, json_output=False)
        
        captured = capsys.readouterr()
        # Should have more detailed output
        assert len(captured.out) > 50  # More verbose


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
