#!/usr/bin/env python3
"""Tests for og.xts - Multi-repo git operations.

Tests cover:
- YAML structure and parsing
- Command definitions and descriptions
- URL conversion (SSH → HTTPS)
- Command group definitions
- Metadata fields (brief, alias_name)
- Shell command POSIX compatibility
- Individual command execution (version, current_branch, branch, help_commands)
"""

import os
import sys
import subprocess
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import yaml


# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────

OG_XTS_PATH = Path(__file__).parent.parent / "examples" / "og.xts"


@pytest.fixture(scope="module")
def og_config():
    """Load and parse the og.xts file."""
    with open(OG_XTS_PATH) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def og_commands(og_config):
    """Extract commands (dicts with 'command' key) from config."""
    return {
        k: v for k, v in og_config.items()
        if isinstance(v, dict) and "command" in v
    }


@pytest.fixture
def temp_git_repo(tmp_path):
    """Create a temporary git repository for testing."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo_dir, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_dir, capture_output=True,
    )
    # Create initial commit so branch exists
    (repo_dir / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_dir, capture_output=True,
    )
    return repo_dir


@pytest.fixture
def temp_git_repo_with_remote(temp_git_repo):
    """Create a temp git repo with a fake remote."""
    subprocess.run(
        ["git", "remote", "add", "origin", "git@github.com:testorg/testrepo.git"],
        cwd=temp_git_repo, capture_output=True,
    )
    return temp_git_repo


@pytest.fixture
def multi_repo_tree(tmp_path):
    """Create a directory with multiple nested git repos."""
    repos = []
    for name in ["repo_alpha", "repo_beta", "repo_gamma"]:
        repo_dir = tmp_path / name
        repo_dir.mkdir()
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_dir, capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_dir, capture_output=True,
        )
        (repo_dir / "README.md").write_text(f"# {name}\n")
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_dir, capture_output=True,
        )
        repos.append(repo_dir)
    return tmp_path, repos


# ──────────────────────────────────────────────────────────────────────
# 1. YAML structure and parsing
# ──────────────────────────────────────────────────────────────────────

class TestYAMLStructure:

    def test_og_xts_file_exists(self):
        assert OG_XTS_PATH.exists()

    def test_og_xts_parses_as_yaml(self, og_config):
        assert isinstance(og_config, dict)

    def test_brief_field(self, og_config):
        assert "brief" in og_config
        assert "git" in og_config["brief"].lower()

    def test_alias_name_field(self, og_config):
        assert og_config.get("alias_name") == "og"

    def test_command_groups_defined(self, og_config):
        assert "command_groups" in og_config
        groups = og_config["command_groups"]
        assert "info" in groups
        assert "operations" in groups
        assert "meta" in groups

    def test_command_groups_have_required_fields(self, og_config):
        for gname, group in og_config["command_groups"].items():
            assert "title" in group, f"Group {gname} missing title"
            assert "commands" in group, f"Group {gname} missing commands"
            assert isinstance(group["commands"], list)

    def test_all_grouped_commands_exist(self, og_config, og_commands):
        """Every command referenced in command_groups should be a real command."""
        for gname, group in og_config["command_groups"].items():
            for cmd_name in group["commands"]:
                assert cmd_name in og_commands, \
                    f"Group '{gname}' references '{cmd_name}' but it's not defined"


# ──────────────────────────────────────────────────────────────────────
# 2. Command definitions
# ──────────────────────────────────────────────────────────────────────

EXPECTED_COMMANDS = [
    "version",
    "branches",
    "branch",
    "current_branch",
    "remote",
    "url",
    "status",
    "cmd",
    "help_commands",
]


class TestCommandDefinitions:

    @pytest.mark.parametrize("cmd_name", EXPECTED_COMMANDS)
    def test_command_exists(self, og_commands, cmd_name):
        assert cmd_name in og_commands

    @pytest.mark.parametrize("cmd_name", EXPECTED_COMMANDS)
    def test_command_has_description(self, og_commands, cmd_name):
        cmd = og_commands[cmd_name]
        assert "description" in cmd
        assert len(cmd["description"].strip()) > 0

    @pytest.mark.parametrize("cmd_name", EXPECTED_COMMANDS)
    def test_command_has_command_field(self, og_commands, cmd_name):
        cmd = og_commands[cmd_name]
        assert "command" in cmd
        assert isinstance(cmd["command"], str)
        assert len(cmd["command"].strip()) > 0

    def test_total_command_count(self, og_commands):
        assert len(og_commands) == len(EXPECTED_COMMANDS)

    def test_multi_repo_commands_have_passthrough(self, og_commands):
        """Multi-repo commands need passthrough for -s, -d, -n, -l flags."""
        multi_repo = ["branches", "remote", "status", "cmd", "url", "branch",
                       "current_branch"]
        for name in multi_repo:
            cmd = og_commands[name]
            params = cmd.get("params", {})
            assert params.get("passthrough") is True, \
                f"'{name}' should have passthrough: true"


# ──────────────────────────────────────────────────────────────────────
# 3. Shell command POSIX compatibility
# ──────────────────────────────────────────────────────────────────────

class TestPOSIXCompatibility:

    def test_no_echo_dash_e(self, og_commands):
        """Commands should not use echo -e (not POSIX)."""
        for name, cmd in og_commands.items():
            script = cmd["command"]
            # Check for echo -e at start of line or after semicolon
            lines = script.split('\n')
            for i, line in enumerate(lines):
                stripped = line.strip()
                assert not stripped.startswith('echo -e'), \
                    f"'{name}' line {i+1}: uses 'echo -e' (not POSIX). Use plain echo."

    def test_no_mapfile(self, og_commands):
        """Commands should not use mapfile (bash-only)."""
        for name, cmd in og_commands.items():
            assert "mapfile" not in cmd["command"], \
                f"'{name}' uses 'mapfile' (bash-only)"

    def test_no_process_substitution(self, og_commands):
        """Commands should not use <(...) (bash-only)."""
        for name, cmd in og_commands.items():
            assert "<(" not in cmd["command"], \
                f"'{name}' uses process substitution '<(...)' (bash-only)"

    def test_no_bash_arrays(self, og_commands):
        """Commands should not use bash array syntax."""
        for name, cmd in og_commands.items():
            # Check for array declaration like VAR=() or VAR=(...)
            import re
            if re.search(r'\w+=\(', cmd["command"]):
                pytest.fail(f"'{name}' uses bash array syntax")


# ──────────────────────────────────────────────────────────────────────
# 4. URL conversion
# ──────────────────────────────────────────────────────────────────────

class TestURLConversion:
    """Test the SSH → HTTPS URL conversion logic."""

    def _run_conversion(self, remote_url):
        """Run the _remote_to_https function via shell."""
        script = """
        _remote_to_https() {
          _r="$1"
          if echo "$_r" | grep -q "^http"; then
            echo "$_r" | sed 's/\\.git$//'
          else
            _host=$(echo "$_r" | sed -E 's|.*@([^:/]+)[:/].*|\\1|')
            _rpath=$(echo "$_r" | sed -E 's|.*@[^:/]+[:/](.+)$|\\1|' | sed 's/\\.git$//')
            echo "https://${_host}/${_rpath}"
          fi
        }
        _remote_to_https "%s"
        """ % remote_url
        result = subprocess.run(
            ["/bin/sh", "-c", script],
            capture_output=True, text=True,
        )
        return result.stdout.strip()

    def test_github_ssh(self):
        url = self._run_conversion("git@github.com:rdkcentral/xts_core.git")
        assert url == "https://github.com/rdkcentral/xts_core"

    def test_github_https(self):
        url = self._run_conversion("https://github.com/rdkcentral/xts_core.git")
        assert url == "https://github.com/rdkcentral/xts_core"

    def test_github_https_no_git_suffix(self):
        url = self._run_conversion("https://github.com/rdkcentral/xts_core")
        assert url == "https://github.com/rdkcentral/xts_core"

    def test_gitlab_ssh(self):
        url = self._run_conversion("git@gitlab.com:myorg/myproject.git")
        assert url == "https://gitlab.com/myorg/myproject"

    def test_ssh_protocol(self):
        url = self._run_conversion("ssh://git@github.com/rdkcentral/xts_core.git")
        assert url == "https://github.com/rdkcentral/xts_core"

    def test_nested_path_ssh(self):
        url = self._run_conversion("git@github.com:org/sub/repo.git")
        assert url == "https://github.com/org/sub/repo"

    def test_http_remote(self):
        url = self._run_conversion("http://github.com/rdkcentral/xts_core.git")
        assert url == "http://github.com/rdkcentral/xts_core"


# ──────────────────────────────────────────────────────────────────────
# 5. Command execution (using temp git repos)
# ──────────────────────────────────────────────────────────────────────

class TestCommandExecution:
    """Test actual command execution via xts."""

    def _run_og(self, command, *args, cwd=None):
        """Run an og.xts command via Python."""
        cmd = [
            sys.executable, "-m", "xts_core.xts",
            str(OG_XTS_PATH), command, *args,
        ]
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).parent.parent / "src")
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=cwd, env=env,
        )
        return result

    def test_version_output(self):
        result = self._run_og("version")
        assert "2.0.0" in result.stdout
        assert "Operate on Git" in result.stdout

    def test_help_commands_output(self):
        result = self._run_og("help_commands")
        assert "branches" in result.stdout
        assert "status" in result.stdout
        assert "cmd" in result.stdout
        assert "url" in result.stdout

    def test_current_branch_in_git_repo(self, temp_git_repo):
        result = self._run_og("current_branch", cwd=str(temp_git_repo))
        # Should output a branch name (master or main)
        branch = result.stdout.strip()
        assert branch in ("master", "main"), f"Got: {branch}"

    def test_current_branch_verbose(self, temp_git_repo):
        result = self._run_og("current_branch", "-v", cwd=str(temp_git_repo))
        # Should show commit hash + message
        assert "Initial commit" in result.stdout

    def test_branch_shows_header(self, temp_git_repo):
        result = self._run_og("branch", cwd=str(temp_git_repo))
        assert "Branches" in result.stdout

    def test_branch_not_git_repo(self, tmp_path):
        result = self._run_og("branch", cwd=str(tmp_path))
        assert result.returncode != 0

    def test_status_finds_repos(self, multi_repo_tree):
        parent, repos = multi_repo_tree
        result = self._run_og("status", cwd=str(parent))
        assert "Status" in result.stdout
        assert "clean" in result.stdout

    def test_status_summary(self, multi_repo_tree):
        parent, repos = multi_repo_tree
        result = self._run_og("status", cwd=str(parent))
        assert "Summary" in result.stdout
        assert "3 clean" in result.stdout

    def test_status_detects_dirty(self, multi_repo_tree):
        parent, repos = multi_repo_tree
        # Make one repo dirty
        (repos[0] / "dirty.txt").write_text("dirty\n")
        result = self._run_og("status", cwd=str(parent))
        assert "dirty" in result.stdout
        assert "2 clean" in result.stdout
        assert "1 dirty" in result.stdout

    def test_remote_finds_repos(self, multi_repo_tree):
        parent, repos = multi_repo_tree
        result = self._run_og("remote", cwd=str(parent))
        assert "Remotes" in result.stdout
        assert "3 repos" in result.stdout
        # repos have no remote, should show "(no remote)"
        assert "no remote" in result.stdout

    def test_remote_with_directory_filter(self, multi_repo_tree):
        parent, repos = multi_repo_tree
        result = self._run_og("remote", "-d", "alpha", cwd=str(parent))
        assert "repo_alpha" in result.stdout
        assert "1 repos displayed" in result.stdout

    def test_branches_finds_repos(self, multi_repo_tree):
        parent, repos = multi_repo_tree
        result = self._run_og("branches", cwd=str(parent))
        assert "Branches" in result.stdout
        assert "3 repos" in result.stdout

    def test_branches_with_search(self, multi_repo_tree):
        parent, repos = multi_repo_tree
        # Create a feature branch in one repo
        subprocess.run(
            ["git", "checkout", "-b", "feature/test"],
            cwd=repos[0], capture_output=True,
        )
        result = self._run_og("branches", "-s", "feature", cwd=str(parent))
        assert "feature" in result.stdout

    def test_no_repos_found(self, tmp_path):
        """No .git directories below → graceful message."""
        result = self._run_og("status", cwd=str(tmp_path))
        assert "No git repos" in result.stdout

    def test_url_finds_repos(self, multi_repo_tree):
        parent, repos = multi_repo_tree
        # Add a remote to one repo
        subprocess.run(
            ["git", "remote", "add", "origin", "git@github.com:test/repo_alpha.git"],
            cwd=repos[0], capture_output=True,
        )
        result = self._run_og("url", cwd=str(parent))
        assert "URLs" in result.stdout
        assert "github.com" in result.stdout

    def test_url_specific_path(self, temp_git_repo_with_remote):
        result = self._run_og(
            "url", str(temp_git_repo_with_remote / "README.md"),
            cwd=str(temp_git_repo_with_remote),
        )
        assert "blob" in result.stdout
        assert "README.md" in result.stdout

    def test_url_directory_path(self, temp_git_repo_with_remote):
        result = self._run_og(
            "url", str(temp_git_repo_with_remote),
            cwd=str(temp_git_repo_with_remote),
        )
        assert "tree" in result.stdout


# ──────────────────────────────────────────────────────────────────────
# 6. Description quality
# ──────────────────────────────────────────────────────────────────────

class TestDescriptionQuality:

    @pytest.mark.parametrize("cmd_name", EXPECTED_COMMANDS)
    def test_first_line_not_empty(self, og_commands, cmd_name):
        desc = og_commands[cmd_name]["description"]
        first_line = desc.strip().splitlines()[0]
        assert len(first_line) > 5

    def test_multi_repo_commands_show_usage(self, og_commands):
        """Multi-repo commands should include usage examples."""
        for name in ["branches", "status", "cmd", "url", "remote"]:
            desc = og_commands[name]["description"]
            assert "usage" in desc.lower() or "xts og" in desc.lower(), \
                f"'{name}' description should include usage"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
