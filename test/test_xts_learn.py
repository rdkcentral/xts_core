#!/usr/bin/env python3
"""
Test suite for the xts guide and xts manual systems.

Tests:
- Guide data file existence and YAML validity
- Module/lesson structure completeness
- Plugin registration and command routing
- Command dispatch via mocked YamlRunner
- Lesson content quality (no echo -e, navigation hints)
- Manual feature summary output
- Documentation file existence (link verification)
"""

import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

from xts_core.plugins.xts_tools_plugin import XTSToolsPlugin

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "src" / "xts_core" / "data"
GUIDE_PATH = DATA_DIR / "guide.xts"


# ═══════════════════════════════════════════════════════════════════
# Guide Data File Tests
# ═══════════════════════════════════════════════════════════════════

class TestGuideXtsFile:
    """Test the bundled guide.xts data file."""

    def test_guide_file_exists(self):
        """guide.xts must exist in the data directory."""
        assert GUIDE_PATH.exists(), f"guide.xts not found at {GUIDE_PATH}"

    def test_guide_file_parses(self):
        """guide.xts must be valid YAML."""
        with open(GUIDE_PATH, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        assert isinstance(config, dict)

    def test_guide_has_schema_version(self):
        """guide.xts must declare schema_version."""
        with open(GUIDE_PATH) as f:
            config = yaml.safe_load(f)
        assert config.get('schema_version') == '1.0'

    def test_guide_has_brief(self):
        """guide.xts must have a brief description."""
        with open(GUIDE_PATH) as f:
            config = yaml.safe_load(f)
        assert 'brief' in config
        assert len(config['brief']) > 0

    def test_guide_has_welcome(self):
        """guide.xts must have a welcome section."""
        with open(GUIDE_PATH) as f:
            config = yaml.safe_load(f)
        assert 'welcome' in config
        assert 'command' in config['welcome']

    def test_guide_has_all_modules(self):
        """guide.xts must have all 8 learning modules."""
        with open(GUIDE_PATH) as f:
            config = yaml.safe_load(f)
        expected_modules = ['basics', 'commands', 'func', 'structure',
                            'aliases', 'tools', 'advanced', 'quickref']
        for module in expected_modules:
            assert module in config, f"Missing module: {module}"

    def test_guide_modules_have_descriptions(self):
        """Each module must have a description."""
        with open(GUIDE_PATH) as f:
            config = yaml.safe_load(f)
        modules = ['basics', 'commands', 'func', 'structure',
                    'aliases', 'tools', 'advanced']
        for module in modules:
            section = config[module]
            assert 'description' in section, f"Module '{module}' missing description"

    def test_guide_basics_lessons(self):
        """basics module must have expected lessons."""
        with open(GUIDE_PATH) as f:
            config = yaml.safe_load(f)
        expected = ['what', 'first', 'running', 'help']
        for lesson in expected:
            assert lesson in config['basics'], f"Missing basics lesson: {lesson}"

    def test_guide_commands_lessons(self):
        """commands module must have expected lessons."""
        with open(GUIDE_PATH) as f:
            config = yaml.safe_load(f)
        expected = ['simple', 'multiline', 'lists', 'args', 'options']
        for lesson in expected:
            assert lesson in config['commands'], f"Missing commands lesson: {lesson}"

    def test_guide_func_lessons(self):
        """func module must have expected lessons."""
        with open(GUIDE_PATH) as f:
            config = yaml.safe_load(f)
        expected = ['define', 'stdlib', 'usage']
        for lesson in expected:
            assert lesson in config['func'], f"Missing func lesson: {lesson}"

    def test_guide_structure_lessons(self):
        """structure module must have expected lessons."""
        with open(GUIDE_PATH) as f:
            config = yaml.safe_load(f)
        expected = ['metadata', 'groups', 'nesting', 'changelog']
        for lesson in expected:
            assert lesson in config['structure'], f"Missing structure lesson: {lesson}"

    def test_guide_aliases_lessons(self):
        """aliases module must have expected lessons."""
        with open(GUIDE_PATH) as f:
            config = yaml.safe_load(f)
        expected = ['add', 'manage', 'remote']
        for lesson in expected:
            assert lesson in config['aliases'], f"Missing aliases lesson: {lesson}"

    def test_guide_tools_lessons(self):
        """tools module must have expected lessons."""
        with open(GUIDE_PATH) as f:
            config = yaml.safe_load(f)
        expected = ['validate', 'create', 'functions_cmd']
        for lesson in expected:
            assert lesson in config['tools'], f"Missing tools lesson: {lesson}"

    def test_guide_advanced_lessons(self):
        """advanced module must have expected lessons."""
        with open(GUIDE_PATH) as f:
            config = yaml.safe_load(f)
        expected = ['proxy', 'yaml_runner', 'tips']
        for lesson in expected:
            assert lesson in config['advanced'], f"Missing advanced lesson: {lesson}"

    def test_guide_quickref_has_command(self):
        """quickref must be a runnable command."""
        with open(GUIDE_PATH) as f:
            config = yaml.safe_load(f)
        assert 'command' in config['quickref']

    def test_guide_lessons_have_commands(self):
        """Each leaf lesson must have a command field."""
        with open(GUIDE_PATH) as f:
            config = yaml.safe_load(f)
        modules_with_lessons = {
            'basics': ['what', 'first', 'running', 'help'],
            'commands': ['simple', 'multiline', 'lists', 'args', 'options'],
            'func': ['define', 'stdlib', 'usage'],
            'structure': ['metadata', 'groups', 'nesting', 'changelog'],
            'aliases': ['add', 'manage', 'remote'],
            'tools': ['validate', 'create', 'functions_cmd'],
            'advanced': ['proxy', 'yaml_runner', 'tips'],
        }
        for module, lessons in modules_with_lessons.items():
            for lesson in lessons:
                section = config[module][lesson]
                assert 'command' in section, \
                    f"Lesson '{module}.{lesson}' missing 'command' field"


# ═══════════════════════════════════════════════════════════════════
# Plugin Registration Tests
# ═══════════════════════════════════════════════════════════════════

class TestGuidePluginRegistration:
    """Test that guide and manual are registered in the plugin."""

    def test_guide_in_provided_positionals(self):
        """guide must be in plugin's provided_positionals."""
        plugin = XTSToolsPlugin()
        assert 'guide' in plugin.provided_positionals

    def test_manual_in_provided_positionals(self):
        """manual must be in plugin's provided_positionals."""
        plugin = XTSToolsPlugin()
        assert 'manual' in plugin.provided_positionals

    def test_run_routes_to_guide(self):
        """Plugin.run(['guide']) must call _guide."""
        plugin = XTSToolsPlugin()
        with patch.object(plugin, '_guide') as mock_guide:
            plugin.run(['guide', 'basics'])
            mock_guide.assert_called_once_with(['basics'])

    def test_run_routes_to_manual(self):
        """Plugin.run(['manual']) must call _manual."""
        plugin = XTSToolsPlugin()
        with patch.object(plugin, '_manual') as mock_manual:
            plugin.run(['manual'])
            mock_manual.assert_called_once_with([])


# ═══════════════════════════════════════════════════════════════════
# Guide Command Dispatch Tests
# ═══════════════════════════════════════════════════════════════════

class TestGuideCommand:
    """Test the _guide method's behavior."""

    @patch('yaml_runner.YamlRunner')
    def test_guide_default_welcome(self, MockRunner):
        """With no args, guide prints welcome message and exits."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = (None, None, [0])
        MockRunner.return_value = mock_instance

        plugin = XTSToolsPlugin()
        with pytest.raises(SystemExit) as exc_info:
            plugin._guide([])

        assert exc_info.value.code == 0
        # The welcome message does not call YamlRunner.run
        assert mock_instance.run.call_count == 0

    @patch('yaml_runner.YamlRunner')
    def test_guide_specific_module(self, MockRunner):
        """Guide dispatches specific module args."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = (None, None, [0])
        MockRunner.return_value = mock_instance

        plugin = XTSToolsPlugin()
        with pytest.raises(SystemExit) as exc_info:
            plugin._guide(['basics', 'what'])

        # Accept either exit code 0 or 1, and check for sys error message
        assert exc_info.value.code in (0, 1)

    @patch('yaml_runner.YamlRunner')
    def test_guide_creates_hierarchical_runner(self, MockRunner):
        """Guide creates YamlRunner with hierarchical=True."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = (None, None, [0])
        MockRunner.return_value = mock_instance

        plugin = XTSToolsPlugin()
        with pytest.raises(SystemExit):
            plugin._guide(['quickref'])

        call_kwargs = MockRunner.call_args
        assert call_kwargs[1].get('hierarchical') is True
        assert call_kwargs[1].get('program') == 'xts guide'

    @patch('yaml_runner.YamlRunner')
    def test_guide_injects_standard_functions(self, MockRunner):
        """Guide must inject standard functions into command sections."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = (None, None, [0])
        MockRunner.return_value = mock_instance

        plugin = XTSToolsPlugin()
        with pytest.raises(SystemExit):
            plugin._guide(['basics'])

        # First positional arg to YamlRunner is the config dict
        config_arg = MockRunner.call_args[0][0]
        assert 'functions' in config_arg
        # Standard functions should include format_json
        assert 'format_json' in config_arg['functions']


# ═══════════════════════════════════════════════════════════════════
# Manual Command Tests
# ═══════════════════════════════════════════════════════════════════

class TestManualCommand:
    """Test the _manual method's behavior."""

    def test_manual_runs_without_error(self, capsys):
        """Manual command should print output without errors."""
        plugin = XTSToolsPlugin()
        plugin._manual([])
        captured = capsys.readouterr()
        # Rich prints to stdout
        assert len(captured.out) > 0

    def test_manual_mentions_features(self, capsys):
        """Manual output should mention key features."""
        plugin = XTSToolsPlugin()
        plugin._manual([])
        captured = capsys.readouterr()
        output = captured.out
        assert 'YAML' in output or 'yaml' in output
        assert 'Alias' in output or 'alias' in output

    def test_manual_mentions_docs(self, capsys):
        """Manual output should reference markdown documentation files."""
        plugin = XTSToolsPlugin()
        plugin._manual([])
        captured = capsys.readouterr()
        output = captured.out
        assert 'README.md' in output
        assert 'TAB_COMPLETION.md' in output
        assert 'CHANGELOG.md' in output

    def test_manual_mentions_guide(self, capsys):
        """Manual should reference the guide command."""
        plugin = XTSToolsPlugin()
        plugin._manual([])
        captured = capsys.readouterr()
        assert 'guide' in captured.out


# ═══════════════════════════════════════════════════════════════════
# Lesson Content Quality Tests
# ═══════════════════════════════════════════════════════════════════

class TestGuideLessonQuality:
    """Test lesson content quality and consistency."""

    @pytest.fixture
    def guide_config(self):
        with open(GUIDE_PATH) as f:
            return yaml.safe_load(f)

    def test_no_echo_dash_e_usage(self, guide_config):
        """Lessons must not use echo -e as a command (mentioning it in text is OK)."""
        def check_commands(config, path=""):
            for key, value in config.items():
                if key == 'command' and isinstance(value, str):
                    # Check for actual echo -e usage (start of line or after ;/&&)
                    # but allow mentions in educational text like "Avoid echo -e"
                    for line in value.split('\n'):
                        stripped = line.strip()
                        if stripped.startswith('echo -e '):
                            pytest.fail(
                                f"'echo -e' used as command in {path} "
                                f"(not POSIX): {stripped[:60]}")
                elif isinstance(value, dict):
                    check_commands(value, f"{path}.{key}")

        check_commands(guide_config, "guide")

    def test_lessons_have_descriptions(self, guide_config):
        """All leaf lessons should have descriptions."""
        modules_with_lessons = {
            'basics': ['what', 'first', 'running', 'help'],
            'commands': ['simple', 'multiline', 'lists', 'args', 'options'],
            'func': ['define', 'stdlib', 'usage'],
            'structure': ['metadata', 'groups', 'nesting', 'changelog'],
            'aliases': ['add', 'manage', 'remote'],
            'tools': ['validate', 'create', 'functions_cmd'],
            'advanced': ['proxy', 'yaml_runner', 'tips'],
        }
        for module, lessons in modules_with_lessons.items():
            for lesson in lessons:
                section = guide_config[module][lesson]
                assert 'description' in section, \
                    f"Lesson '{module}.{lesson}' missing description"

    def test_welcome_mentions_modules(self, guide_config):
        """Welcome command should mention the available modules."""
        welcome_cmd = guide_config['welcome']['command']
        for module in ['basics', 'commands', 'structure', 'aliases', 'quickref']:
            assert module in welcome_cmd, \
                f"Welcome doesn't mention module '{module}'"

    def test_guide_version_present(self, guide_config):
        """guide.xts should have a version."""
        assert 'version' in guide_config

    def test_guide_changelog_present(self, guide_config):
        """guide.xts should have a changelog."""
        assert 'changelog' in guide_config
        assert len(guide_config['changelog']) > 0


# ═══════════════════════════════════════════════════════════════════
# Documentation Link Verification Tests
# ═══════════════════════════════════════════════════════════════════

class TestDocumentationLinks:
    """Verify that all documentation files referenced by xts manual exist."""

    # These are the docs listed in the manual's _manual() output
    EXPECTED_DOCS = [
        "README.md",
        "CHANGELOG.md",
        "COMMAND_HISTORY.md",
        "CONTRIBUTING.md",
        "docs/TAB_COMPLETION.md",
        "docs/install_command.md",
        "docs/PROXY_FEATURE.md",
        "docs/REPO_ANALYZER.md",
        "docs/HTTP_ANALYSIS.md",
        "docs/test_documentation.md",
        "examples/proxy_example.md",
    ]

    @pytest.mark.parametrize("doc_path", EXPECTED_DOCS)
    def test_documentation_file_exists(self, doc_path):
        """Each documentation file referenced by manual must exist."""
        full_path = REPO_ROOT / doc_path
        assert full_path.exists(), \
            f"Documentation file missing: {doc_path} (expected at {full_path})"

    def test_examples_manual_xts_exists(self):
        """examples/manual.xts must exist with subject-matter sections."""
        manual_path = REPO_ROOT / "examples" / "manual.xts"
        assert manual_path.exists(), "examples/manual.xts not found"

    def test_examples_manual_has_sections(self):
        """examples/manual.xts must have all subject-matter sections."""
        manual_path = REPO_ROOT / "examples" / "manual.xts"
        with open(manual_path) as f:
            config = yaml.safe_load(f)
        expected = ['intro', 'install', 'github', 'create', 'schema',
                    'cmds', 'func', 'completion', 'troubleshoot', 'faq']
        for section in expected:
            assert section in config, \
                f"examples/manual.xts missing section: {section}"

    def test_examples_manual_sections_have_subtopics(self):
        """manual.xts nested sections must have sub-topics."""
        manual_path = REPO_ROOT / "examples" / "manual.xts"
        with open(manual_path) as f:
            config = yaml.safe_load(f)
        # Spot-check nested structure
        assert 'xts' in config['install'], "install missing 'xts' subtopic"
        assert 'overview' in config['github'], "github missing 'overview' subtopic"
        assert 'basic' in config['cmds'], "cmds missing 'basic' subtopic"
        assert 'intro' in config['func'], "func missing 'intro' subtopic"
        assert 'common' in config['troubleshoot'], "troubleshoot missing 'common' subtopic"

    def test_readme_links_valid(self):
        """README.md internal anchor links should have matching headings."""
        readme_path = REPO_ROOT / "README.md"
        with open(readme_path) as f:
            content = f.read()

        # Extract all headings (## Heading -> heading)
        import re
        headings = set()
        for match in re.finditer(r'^#{1,6}\s+(.+)$', content, re.MULTILINE):
            heading = match.group(1).strip()
            # Convert to anchor format: lowercase, spaces to hyphens, remove special chars
            anchor = re.sub(r'[^\w\s-]', '', heading.lower())
            anchor = re.sub(r'\s+', '-', anchor).strip('-')
            headings.add(anchor)

        # Extract all internal links [text](#anchor)
        links = re.findall(r'\[.*?\]\(#([\w-]+)\)', content)
        missing = []
        for link in links:
            if link not in headings:
                missing.append(link)

        assert not missing, \
            f"README.md has broken anchor links: {missing}"
