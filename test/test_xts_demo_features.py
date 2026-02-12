#!/usr/bin/env python3
"""Tests for demo.xts feature subcommands and alias-to-validation pipeline.

Tests cover:
- Schema validation of all example .xts files (demo.xts, manual.xts)
- Feature subcommand parsing and resolution (colors, commands, functions, passthrough, nesting)
- Alias ingestion -> validation pipeline
- Group command handling (features without subcommand shows help)
- Nested command resolution (features -> nesting -> level1 -> level2 -> level3)
- Validation-on-add integration
"""

import os
import sys
import json
import pytest
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from xts_core.xts import XTS
from xts_core.xts_validator import XTSValidator
from xts_core import xts_alias


REPO_ROOT = Path(__file__).parent.parent
EXAMPLES_DIR = REPO_ROOT / "examples"
DEMO_XTS = EXAMPLES_DIR / "demo.xts"
MANUAL_XTS = EXAMPLES_DIR / "manual.xts"

FEATURE_SUBCOMMANDS = ["colors", "commands", "functions", "passthrough", "nesting"]


@pytest.fixture
def validator():
    """Create an XTSValidator instance."""
    return XTSValidator()


@pytest.fixture
def demo_config():
    """Load and return the parsed YAML from demo.xts."""
    with open(DEMO_XTS) as f:
        return yaml.safe_load(f)


@pytest.fixture
def xts_with_demo():
    """Create an XTS instance loaded with demo.xts config."""
    xts = XTS()
    xts.xts_config = str(DEMO_XTS)
    return xts


@pytest.fixture
def temp_xts_home(tmp_path):
    """Create isolated XTS home directory, patching module constants."""
    xts_dir = tmp_path / ".xts"
    cache_dir = xts_dir / "cache"
    cache_dir.mkdir(parents=True)

    original_cache = xts_alias.CACHE_DIR
    original_alias = xts_alias.ALIAS_FILE
    original_metadata = xts_alias.METADATA_FILE

    xts_alias.CACHE_DIR = str(cache_dir)
    xts_alias.ALIAS_FILE = str(xts_dir / "aliases.json")
    xts_alias.METADATA_FILE = str(xts_dir / "metadata.json")

    yield xts_dir

    xts_alias.CACHE_DIR = original_cache
    xts_alias.ALIAS_FILE = original_alias
    xts_alias.METADATA_FILE = original_metadata


# ---------------------------------------------------------------------------
# 1. Schema validation of example files
# ---------------------------------------------------------------------------

class TestExampleFileSchemaValidation:
    """Validate all example .xts files through the XTSValidator."""

    def test_demo_xts_exists(self):
        assert DEMO_XTS.exists(), f"demo.xts not found at {DEMO_XTS}"

    def test_manual_xts_exists(self):
        assert MANUAL_XTS.exists(), f"manual.xts not found at {MANUAL_XTS}"

    def test_demo_xts_parses_as_yaml(self):
        with open(DEMO_XTS) as f:
            config = yaml.safe_load(f)
        assert isinstance(config, dict)
        assert len(config) > 0

    def test_manual_xts_parses_as_yaml(self):
        with open(MANUAL_XTS) as f:
            config = yaml.safe_load(f)
        assert isinstance(config, dict)
        assert len(config) > 0

    def test_demo_xts_validates_without_errors(self, validator):
        is_valid, errors, warnings = validator.validate_file(str(DEMO_XTS))
        assert is_valid, f"demo.xts validation errors: {errors}"

    def test_manual_xts_validates_without_errors(self, validator):
        is_valid, errors, warnings = validator.validate_file(str(MANUAL_XTS))
        assert is_valid, f"manual.xts validation errors: {errors}"

    def test_demo_xts_has_schema_version(self, demo_config):
        assert "schema_version" in demo_config
        assert demo_config["schema_version"] == "1.0"

    def test_demo_xts_has_version(self, demo_config):
        assert "version" in demo_config

    @pytest.mark.parametrize("example_file", [
        pytest.param(DEMO_XTS, id="demo"),
        pytest.param(MANUAL_XTS, id="manual"),
    ])
    def test_all_examples_validate(self, validator, example_file):
        if not example_file.exists():
            pytest.skip(f"{example_file} not present")
        is_valid, errors, warnings = validator.validate_file(str(example_file))
        assert is_valid, f"{example_file.name} validation errors: {errors}"


# ---------------------------------------------------------------------------
# 2. Feature subcommand parsing and resolution
# ---------------------------------------------------------------------------

class TestDemoFeatureSubcommandParsing:
    """Test that each demo features subcommand can be parsed and resolved."""

    def test_features_section_exists_in_config(self, demo_config):
        assert "features" in demo_config
        assert isinstance(demo_config["features"], dict)

    def test_features_is_a_command_group(self, demo_config):
        features = demo_config["features"]
        assert "command" not in features, "features is a group, not a leaf command"

    @pytest.mark.parametrize("subcommand", FEATURE_SUBCOMMANDS)
    def test_feature_subcommand_exists(self, demo_config, subcommand):
        assert subcommand in demo_config["features"], \
            f"Missing subcommand: features.{subcommand}"

    @pytest.mark.parametrize("subcommand", ["colors", "commands", "functions", "passthrough"])
    def test_leaf_feature_has_command_key(self, demo_config, subcommand):
        section = demo_config["features"][subcommand]
        assert "command" in section, \
            f"features.{subcommand} is missing 'command' key"

    def test_nesting_is_a_group(self, demo_config):
        nesting = demo_config["features"]["nesting"]
        assert "command" not in nesting
        assert "level1" in nesting

    @pytest.mark.parametrize("subcommand", FEATURE_SUBCOMMANDS)
    def test_feature_subcommand_has_description(self, demo_config, subcommand):
        section = demo_config["features"][subcommand]
        assert "description" in section

    def test_passthrough_has_params(self, demo_config):
        passthrough = demo_config["features"]["passthrough"]
        assert "params" in passthrough
        assert passthrough["params"].get("passthrough") is True

    @pytest.mark.parametrize("subcommand", FEATURE_SUBCOMMANDS)
    def test_xts_finds_feature_node(self, xts_with_demo, subcommand):
        node = xts_with_demo._find_node_for_path(["features", subcommand])
        assert node is not None, \
            f"Could not resolve path: features -> {subcommand}"
        assert isinstance(node, dict)

    def test_features_extracted_as_command_section(self, xts_with_demo):
        assert "features" in xts_with_demo._command_sections


# ---------------------------------------------------------------------------
# 3. Group command handling
# ---------------------------------------------------------------------------

class TestGroupCommandHandling:
    """Test group command handling -- running a group without subcommand."""

    @patch('xts_core.xts.Console')
    def test_features_group_shows_usage(self, mock_console_cls, xts_with_demo):
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        xts_with_demo._runtime_context["alias_name"] = "demo"
        result = xts_with_demo._show_group_usage_if_needed(["features"])

        assert result is True, "Group usage handler should return True for 'features'"
        assert mock_console.print.called

    @patch('xts_core.xts.Console')
    def test_features_group_lists_all_subcommands(self, mock_console_cls, xts_with_demo):
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        xts_with_demo._runtime_context["alias_name"] = "demo"
        xts_with_demo._show_group_usage_if_needed(["features"])

        printed_text = " ".join(str(c) for c in mock_console.print.call_args_list)
        for subcommand in FEATURE_SUBCOMMANDS:
            assert subcommand in printed_text, \
                f"Subcommand '{subcommand}' not shown in group usage"

    @patch('xts_core.xts.Console')
    def test_nesting_group_shows_usage(self, mock_console_cls, xts_with_demo):
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        xts_with_demo._runtime_context["alias_name"] = "demo"
        result = xts_with_demo._show_group_usage_if_needed(["features", "nesting"])

        assert result is True

    def test_leaf_command_does_not_trigger_group_usage(self, xts_with_demo):
        result = xts_with_demo._show_group_usage_if_needed(["features", "colors"])
        assert result is False

    def test_nonexistent_path_does_not_trigger_group_usage(self, xts_with_demo):
        result = xts_with_demo._show_group_usage_if_needed(["nonexistent"])
        assert result is False

    @patch('xts_core.xts.Console')
    def test_create_group_shows_usage(self, mock_console_cls, xts_with_demo):
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console
        xts_with_demo._runtime_context["alias_name"] = "demo"
        result = xts_with_demo._show_group_usage_if_needed(["create"])
        assert result is True

    @patch('xts_core.xts.Console')
    def test_workflow_group_shows_usage(self, mock_console_cls, xts_with_demo):
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console
        xts_with_demo._runtime_context["alias_name"] = "demo"
        result = xts_with_demo._show_group_usage_if_needed(["workflow"])
        assert result is True

    def test_empty_args_returns_false(self, xts_with_demo):
        assert xts_with_demo._show_group_usage_if_needed([]) is False

    def test_flag_only_args_returns_false(self, xts_with_demo):
        assert xts_with_demo._show_group_usage_if_needed(["--help"]) is False


# ---------------------------------------------------------------------------
# 4. Nested command resolution
# ---------------------------------------------------------------------------

class TestNestedCommandResolution:
    """Test nested command resolution for deeply nested structures."""

    def test_resolve_nesting_level1(self, xts_with_demo):
        node = xts_with_demo._find_node_for_path(["features", "nesting", "level1"])
        assert node is not None
        assert "command" in node

    def test_resolve_nesting_level2(self, xts_with_demo):
        node = xts_with_demo._find_node_for_path(
            ["features", "nesting", "level1", "level2"]
        )
        assert node is not None
        assert "command" in node

    def test_resolve_nesting_level3(self, xts_with_demo):
        node = xts_with_demo._find_node_for_path(
            ["features", "nesting", "level1", "level2", "level3"]
        )
        assert node is not None
        assert "command" in node

    def test_level1_has_both_command_and_children(self, xts_with_demo):
        node = xts_with_demo._find_node_for_path(["features", "nesting", "level1"])
        assert "command" in node
        assert "level2" in node

    def test_nonexistent_level4_returns_none(self, xts_with_demo):
        node = xts_with_demo._find_node_for_path(
            ["features", "nesting", "level1", "level2", "level3", "level4"]
        )
        assert node is None

    def test_get_group_subcommands_for_nesting(self, xts_with_demo):
        nesting_node = xts_with_demo._find_node_for_path(["features", "nesting"])
        subcommands = xts_with_demo._get_group_subcommands(nesting_node)
        subcommand_names = [name for name, _ in subcommands]
        assert "level1" in subcommand_names

    def test_get_group_subcommands_for_features(self, xts_with_demo):
        features_node = xts_with_demo._find_node_for_path(["features"])
        subcommands = xts_with_demo._get_group_subcommands(features_node)
        subcommand_names = [name for name, _ in subcommands]
        for sub in FEATURE_SUBCOMMANDS:
            assert sub in subcommand_names


# ---------------------------------------------------------------------------
# 5. Alias ingestion -> validation pipeline
# ---------------------------------------------------------------------------

class TestAliasIngestionValidationPipeline:
    """Test alias ingestion followed by validation of cached file."""

    def test_add_demo_as_alias_and_validate_cache(self, temp_xts_home, validator):
        xts_alias.add_alias("demo", str(DEMO_XTS))

        aliases = xts_alias.list_aliases()
        assert "demo" in aliases

        cache_path = aliases["demo"]
        assert os.path.exists(cache_path)

        is_valid, errors, warnings = validator.validate_file(cache_path)
        assert is_valid, f"Cached demo.xts validation errors: {errors}"

    def test_add_manual_as_alias_and_validate_cache(self, temp_xts_home, validator):
        xts_alias.add_alias("manual", str(MANUAL_XTS))

        aliases = xts_alias.list_aliases()
        assert "manual" in aliases

        cache_path = aliases["manual"]
        assert os.path.exists(cache_path)

        is_valid, errors, warnings = validator.validate_file(cache_path)
        assert is_valid, f"Cached manual.xts validation errors: {errors}"

    def test_cached_file_content_matches_source(self, temp_xts_home):
        xts_alias.add_alias("demo", str(DEMO_XTS))

        aliases = xts_alias.list_aliases()
        cache_path = aliases["demo"]

        with open(DEMO_XTS) as f:
            source_content = f.read()
        with open(cache_path) as f:
            cached_content = f.read()

        assert source_content == cached_content

    def test_cached_file_loads_same_commands(self, temp_xts_home, demo_config):
        xts_alias.add_alias("demo", str(DEMO_XTS))

        aliases = xts_alias.list_aliases()
        with open(aliases["demo"]) as f:
            cached_config = yaml.safe_load(f)

        assert cached_config.keys() == demo_config.keys()
        assert "features" in cached_config

    def test_alias_metadata_records_source(self, temp_xts_home):
        xts_alias.add_alias("demo", str(DEMO_XTS))
        metadata = xts_alias.load_metadata()
        assert "demo" in metadata
        assert "source" in metadata["demo"]

    def test_cached_demo_features_subcommands_intact(self, temp_xts_home):
        xts_alias.add_alias("demo", str(DEMO_XTS))

        aliases = xts_alias.list_aliases()
        with open(aliases["demo"]) as f:
            cached_config = yaml.safe_load(f)

        features = cached_config["features"]
        for sub in FEATURE_SUBCOMMANDS:
            assert sub in features, f"Missing '{sub}' in cached features section"


# ---------------------------------------------------------------------------
# 6. Validation-on-add behaviour
# ---------------------------------------------------------------------------

class TestValidationOnAliasAdd:
    """Test validate-on-add for alias ingestion."""

    def test_valid_file_passes_validation(self, temp_xts_home, tmp_path):
        valid_file = tmp_path / "valid.xts"
        valid_file.write_text(
            'schema_version: "1.0"\n'
            'version: "1.0.0"\n'
            'hello:\n'
            '  description: Say hello\n'
            '  command: echo "Hello"\n'
        )

        validator = XTSValidator()
        is_valid, errors, warnings = validator.validate_file(str(valid_file))
        assert is_valid, f"Valid file should pass: {errors}"

        xts_alias.add_alias("valid_test", str(valid_file))
        assert "valid_test" in xts_alias.list_aliases()

    def test_invalid_yaml_is_caught(self, temp_xts_home, tmp_path):
        bad_file = tmp_path / "bad.xts"
        bad_file.write_text("this: is: not: valid: yaml: [[[")

        validator = XTSValidator()
        is_valid, errors, warnings = validator.validate_file(str(bad_file))
        assert not is_valid
        assert len(errors) > 0

    def test_empty_file_is_caught(self, temp_xts_home, tmp_path):
        empty_file = tmp_path / "empty.xts"
        empty_file.write_text("")

        validator = XTSValidator()
        is_valid, errors, warnings = validator.validate_file(str(empty_file))
        assert not is_valid

    def test_file_with_no_commands_produces_warning(self, temp_xts_home, tmp_path):
        no_cmds = tmp_path / "nocmds.xts"
        no_cmds.write_text(
            'schema_version: "1.0"\n'
            'version: "1.0.0"\n'
            'brief: "Empty config"\n'
        )

        validator = XTSValidator()
        is_valid, errors, warnings = validator.validate_file(str(no_cmds))
        assert any("command" in w.lower() or "no command" in w.lower() for w in warnings)

    @patch('xts_core.xts_alias._validate_on_add')
    def test_validate_on_add_called_for_local_file(self, mock_validate, temp_xts_home, tmp_path):
        valid_file = tmp_path / "test.xts"
        valid_file.write_text(
            'schema_version: "1.0"\n'
            'hello:\n'
            '  description: Test\n'
            '  command: echo test\n'
        )
        xts_alias.add_alias("test_val", str(valid_file))
        mock_validate.assert_called_once()
        call_args = mock_validate.call_args
        assert call_args[0][1] == "test_val"


# ---------------------------------------------------------------------------
# 7. Feature command execution resolution
# ---------------------------------------------------------------------------

class TestDemoCommandExecution:
    """Test that feature demo commands can be resolved for execution."""

    @pytest.mark.parametrize("subcommand", ["colors", "commands", "functions", "passthrough"])
    def test_each_leaf_feature_has_executable_command(self, xts_with_demo, subcommand):
        node = xts_with_demo._find_node_for_path(["features", subcommand])
        assert node is not None
        command = node.get("command", "")
        assert command, f"features.{subcommand} has empty command"
        assert len(command.strip()) > 0

    def test_nesting_level1_has_executable_command(self, xts_with_demo):
        node = xts_with_demo._find_node_for_path(["features", "nesting", "level1"])
        assert node is not None
        assert "command" in node
        assert len(node["command"].strip()) > 0

    def test_nesting_level2_has_executable_command(self, xts_with_demo):
        node = xts_with_demo._find_node_for_path(
            ["features", "nesting", "level1", "level2"]
        )
        assert node is not None
        assert "command" in node
        assert len(node["command"].strip()) > 0

    def test_nesting_level3_has_executable_command(self, xts_with_demo):
        node = xts_with_demo._find_node_for_path(
            ["features", "nesting", "level1", "level2", "level3"]
        )
        assert node is not None
        assert "command" in node
        assert len(node["command"].strip()) > 0

    def test_passthrough_params_flag(self, xts_with_demo):
        node = xts_with_demo._find_node_for_path(["features", "passthrough"])
        assert node is not None
        params = node.get("params", {})
        assert params.get("passthrough") is True

    def test_colors_command_contains_ansi_codes(self, xts_with_demo):
        node = xts_with_demo._find_node_for_path(["features", "colors"])
        command = node["command"]
        assert "\\033[" in command or "\033[" in command

    def test_all_demo_top_level_groups_load(self, xts_with_demo):
        sections = xts_with_demo._command_sections
        expected_groups = ["intro", "features", "create", "workflow", "github", "tips", "about"]
        for group in expected_groups:
            assert group in sections, f"Top-level group '{group}' missing from command sections"

    def test_leaf_command_does_not_show_group_usage(self, xts_with_demo):
        for subcommand in ["colors", "commands", "functions", "passthrough"]:
            result = xts_with_demo._show_group_usage_if_needed(
                ["features", subcommand]
            )
            assert result is False, f"features.{subcommand} should be a leaf, not a group"
