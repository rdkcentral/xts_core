#!/usr/bin/env python3
"""Tests for XTS standard function library.

Tests cover:
- Standard function definitions and structure
- Function injection into config
- Validator awareness of standard functions
- User override behavior
- CLI listing command
- Function expansion in commands
"""

import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from xts_core.standard_functions import (
    STANDARD_FUNCTIONS,
    get_standard_functions,
    get_standard_function_names,
)
from xts_core.xts_validator import XTSValidator
from xts_core.xts import XTS
from xts_core.plugins.xts_tools_plugin import XTSToolsPlugin


EXPECTED_FUNCTIONS = [
    "format_json",
    "format_json_raw",
    "format_yaml",
    "format_table",
    "count_lines",
    "sort_unique",
    "trim",
    "to_upper",
    "to_lower",
    "highlight_errors",
    "extract_ips",
    "strip_ansi",
    "csv_to_json",
]


@pytest.fixture
def validator():
    return XTSValidator()


@pytest.fixture
def temp_xts_file(tmp_path):
    """Create a temporary .xts file with given content."""
    def _create(content: str) -> str:
        f = tmp_path / "test.xts"
        f.write_text(content)
        return str(f)
    return _create


# ──────────────────────────────────────────────────────────────────────
# 1. Standard function definitions
# ──────────────────────────────────────────────────────────────────────

class TestStandardFunctionDefinitions:

    def test_standard_functions_is_dict(self):
        assert isinstance(STANDARD_FUNCTIONS, dict)

    def test_non_empty(self):
        assert len(STANDARD_FUNCTIONS) > 0

    @pytest.mark.parametrize("name", EXPECTED_FUNCTIONS)
    def test_expected_function_present(self, name):
        assert name in STANDARD_FUNCTIONS

    @pytest.mark.parametrize("name", EXPECTED_FUNCTIONS)
    def test_function_has_command(self, name):
        assert "command" in STANDARD_FUNCTIONS[name]
        assert isinstance(STANDARD_FUNCTIONS[name]["command"], str)
        assert len(STANDARD_FUNCTIONS[name]["command"]) > 0

    @pytest.mark.parametrize("name", EXPECTED_FUNCTIONS)
    def test_function_has_description(self, name):
        assert "description" in STANDARD_FUNCTIONS[name]
        assert isinstance(STANDARD_FUNCTIONS[name]["description"], str)

    def test_get_standard_functions_returns_copy(self):
        copy1 = get_standard_functions()
        copy1["_test_mutate"] = {"command": "echo test"}
        copy2 = get_standard_functions()
        assert "_test_mutate" not in copy2

    def test_get_standard_function_names_returns_set(self):
        names = get_standard_function_names()
        assert isinstance(names, set)
        assert "format_json" in names

    def test_names_match_dict_keys(self):
        assert get_standard_function_names() == set(STANDARD_FUNCTIONS.keys())


# ──────────────────────────────────────────────────────────────────────
# 2. Function injection into config
# ──────────────────────────────────────────────────────────────────────

class TestFunctionInjection:

    def test_inject_into_empty_config(self):
        config = {"test": {"command": "echo hi"}}
        result = XTS._inject_standard_functions(config)
        assert "functions" in result
        assert "format_json" in result["functions"]

    def test_user_functions_override_standard(self):
        config = {
            "functions": {
                "format_json": {
                    "description": "Custom JSON formatter",
                    "command": "python3 -m json.tool",
                }
            },
            "test": {"command": "echo | {{format_json}}"},
        }
        result = XTS._inject_standard_functions(config)
        assert result["functions"]["format_json"]["command"] == "python3 -m json.tool"

    def test_user_functions_preserved(self):
        config = {
            "functions": {
                "my_custom_func": {
                    "description": "Custom function",
                    "command": "echo custom",
                }
            },
        }
        result = XTS._inject_standard_functions(config)
        assert "my_custom_func" in result["functions"]
        assert "format_json" in result["functions"]

    def test_standard_functions_all_present_in_merged(self):
        config = {}
        result = XTS._inject_standard_functions(config)
        for name in EXPECTED_FUNCTIONS:
            assert name in result["functions"]

    def test_original_config_not_mutated(self):
        config = {"test": {"command": "echo hi"}}
        XTS._inject_standard_functions(config)
        assert "functions" not in config


# ──────────────────────────────────────────────────────────────────────
# 3. Validator recognizes standard functions
# ──────────────────────────────────────────────────────────────────────

class TestValidatorWithStandardFunctions:

    def test_standard_function_placeholder_passes(self, validator, temp_xts_file):
        """Using {{format_json}} without defining it should pass."""
        content = """commands:
  test:
    description: Test
    command: echo '{}' | {{format_json}}
"""
        path = temp_xts_file(content)
        is_valid, errors, warnings = validator.validate_file(path)
        assert not any("unknown" in e.lower() for e in errors), f"Unexpected errors: {errors}"

    def test_standard_function_in_formatter_passes(self, validator, temp_xts_file):
        content = """commands:
  test:
    description: Test
    command: echo '{}'
    formatter: "{{format_json}}"
"""
        path = temp_xts_file(content)
        is_valid, errors, warnings = validator.validate_file(path)
        assert not any("unknown" in e.lower() for e in errors), f"Unexpected errors: {errors}"

    def test_undefined_function_still_errors(self, validator, temp_xts_file):
        content = """commands:
  test:
    description: Test
    command: echo | {{totally_nonexistent_func}}
"""
        path = temp_xts_file(content)
        is_valid, errors, warnings = validator.validate_file(path)
        assert any("unknown" in e.lower() or "totally_nonexistent_func" in e for e in errors)

    def test_user_override_of_standard_passes(self, validator, temp_xts_file):
        content = """functions:
  format_json:
    description: My custom JSON
    command: python3 -m json.tool

commands:
  test:
    description: Test
    command: echo '{}' | {{format_json}}
"""
        path = temp_xts_file(content)
        is_valid, errors, warnings = validator.validate_file(path)
        assert not any("unknown" in e.lower() for e in errors)

    @pytest.mark.parametrize("func_name", EXPECTED_FUNCTIONS)
    def test_each_standard_function_validates(self, validator, temp_xts_file, func_name):
        content = f"""commands:
  test:
    description: Test {func_name}
    command: echo test | {{{{{func_name}}}}}
"""
        path = temp_xts_file(content)
        is_valid, errors, warnings = validator.validate_file(path)
        assert not any(func_name in e for e in errors), f"Function {func_name} flagged: {errors}"


# ──────────────────────────────────────────────────────────────────────
# 4. Function expansion
# ──────────────────────────────────────────────────────────────────────

class TestFunctionExpansion:

    def test_format_json_expands(self):
        config = {"test": {"command": "echo '{}' | {{format_json}}"}}
        merged = XTS._inject_standard_functions(config)
        assert merged["functions"]["format_json"]["command"] == "jq -C ."

    def test_user_override_in_merged_config(self):
        config = {
            "functions": {
                "format_json": {"description": "Mine", "command": "python3 -m json.tool"}
            }
        }
        merged = XTS._inject_standard_functions(config)
        assert merged["functions"]["format_json"]["command"] == "python3 -m json.tool"

    def test_all_standard_functions_have_nonempty_command(self):
        for name, defn in STANDARD_FUNCTIONS.items():
            assert defn["command"].strip(), f"{name} has empty command"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
