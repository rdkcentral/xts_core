#!/usr/bin/env python3
"""Tests for xts_repo_analyzer.py."""

import subprocess
from unittest.mock import patch

from xts_core.xts_repo_analyzer import RepoAnalyzer


class TestCICDDetection:
    """Tests for CI/CD detection behavior."""

    def test_github_actions_is_not_detected(self, tmp_path):
        """GitHub Actions workflows should be ignored by policy."""
        workflows = tmp_path / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci.yml").write_text("name: CI\n")

        analyzer = RepoAnalyzer(str(tmp_path))
        findings = analyzer.analyze()

        assert findings.get("ci_cd") is None

    def test_gitlab_ci_is_detected(self, tmp_path):
        """Other CI providers should still be detected."""
        (tmp_path / ".gitlab-ci.yml").write_text("stages:\n  - test\n")

        analyzer = RepoAnalyzer(str(tmp_path))
        findings = analyzer.analyze()

        assert findings.get("ci_cd") == "GitLab CI"


class TestShallowClone:
    """Tests for shallow clone behavior."""

    @patch("xts_core.xts_repo_analyzer.subprocess.run")
    def test_shallow_clone_success(self, mock_run, tmp_path):
        """Successful shallow clone updates analyzer repo_path."""
        analyzer = RepoAnalyzer(str(tmp_path))
        analyzer.repo_path = tmp_path

        result = analyzer._try_shallow_clone("https://example.com/repo.git")

        assert result is True
        assert analyzer.repo_path == tmp_path / "repo"
        called_cmd = mock_run.call_args[0][0]
        assert called_cmd[:5] == ["git", "clone", "--depth", "1", "--single-branch"]

    @patch(
        "xts_core.xts_repo_analyzer.subprocess.run",
        side_effect=subprocess.CalledProcessError(1, "git", stderr="clone failed"),
    )
    def test_shallow_clone_failure_returns_false(self, _mock_run, tmp_path):
        """Clone failures should gracefully fall back."""
        analyzer = RepoAnalyzer(str(tmp_path))
        analyzer.repo_path = tmp_path

        result = analyzer._try_shallow_clone("https://example.com/repo.git")

        assert result is False
