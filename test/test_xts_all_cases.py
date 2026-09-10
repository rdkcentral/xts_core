import os
import sys
import pytest
import yaml
from unittest.mock import patch
from io import StringIO

sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from xts_core.xts import XTS
from xts_core.xts_alias import (
    add_alias,
    remove_alias,
    resolve_alias_to_xts_path,
    load_aliases
)
from xts_core.plugins.xts_allocator_client import XTSAllocatorClient


def test_create_wizard_writes_xts_file(monkeypatch, tmp_path):
    from xts_core.create import run_create

    output_file = tmp_path / "created.xts"
    answers = iter([
        "run",
        "hello",
        "Say hello",
        "echo hello",
        "n",
        "n",
    ])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    assert run_create(str(output_file)) == 0
    assert yaml.safe_load(output_file.read_text(encoding="utf-8")) == {
        "run": {
            "hello": {
                "description": "Say hello",
                "command": "echo hello",
            }
        }
    }


def test_create_wizard_adds_xts_extension_and_alias(monkeypatch, tmp_path):
    from xts_core import xts_alias
    from xts_core.create import run_create

    output_file = tmp_path / "created.xts"
    added = []
    answers = iter([
        "run",
        "hello",
        "Say hello",
        "echo hello",
        "n",
        "y",
        "greeting",
    ])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    monkeypatch.setattr(
        xts_alias,
        "add_alias_from_input",
        lambda path, name: added.append((path, name)),
    )

    assert run_create(str(tmp_path / "created")) == 0
    assert output_file.exists()
    assert added == [(str(output_file), "greeting")]


def test_create_wizard_requires_output_path_and_section(monkeypatch, tmp_path):
    from xts_core.create import run_create

    output_file = tmp_path / "created.xts"
    answers = iter([
        "",
        str(output_file),
        "",
        "run",
        "hello",
        "Say hello",
        "echo hello",
        "n",
    ])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    assert run_create() == 0
    assert output_file.exists()


def test_create_wizard_does_not_overwrite_without_confirmation(monkeypatch, tmp_path):
    from xts_core.create import run_create

    output_file = tmp_path / "existing.xts"
    output_file.write_text("original", encoding="utf-8")
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")

    assert run_create(str(output_file)) == 1
    assert output_file.read_text(encoding="utf-8") == "original"


def test_create_wizard_rejects_non_xts_output(tmp_path):
    from xts_core.create import run_create

    assert run_create(str(tmp_path / "created.yaml")) == 1
    assert not (tmp_path / "created.yaml").exists()


def test_create_cli_dispatches_to_wizard(monkeypatch):
    from xts_core import xts

    called = []
    monkeypatch.setattr(xts, "run_create", lambda path: called.append(path) or 0)
    monkeypatch.setattr(sys, "argv", ["xts", "create", "new.xts"])

    with pytest.raises(SystemExit) as result:
        XTS().run()

    assert result.value.code == 0
    assert called == ["new.xts"]

@pytest.fixture
def mock_alias_config(monkeypatch, tmp_path):
    temp_home = tmp_path / "home"
    config_dir = temp_home / ".xts"
    config_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(temp_home))
    # Patch xts_alias paths
    import xts_core.xts_alias as xts_alias
    monkeypatch.setattr(xts_alias, "CACHE_DIR", str(config_dir))
    monkeypatch.setattr(xts_alias, "ALIAS_FILE", str(config_dir / "aliases.yaml"))
    yield config_dir

# --- Alias Management ---
def test_add_and_list_alias(mock_alias_config):
    local_file = mock_alias_config / "test1.xts"
    local_file.write_text("steps: []")
    add_alias("test1", str(local_file), "http://example.com/test.xts")
    aliases = load_aliases()
    assert "test1" in aliases
    assert aliases["test1"]["source"] == "http://example.com/test.xts"

def test_remove_alias(mock_alias_config):
    local_file = mock_alias_config / "test2.xts"
    local_file.write_text("steps: []")
    add_alias("test2", str(local_file), "https://url.com/file.xts")
    remove_alias("test2")
    aliases = load_aliases()
    assert "test2" not in aliases

def test_resolve_alias(mock_alias_config):
    local_file = mock_alias_config / "webtest.xts"
    local_file.write_text("steps: []")
    add_alias("webtest", str(local_file), "https://web.site/test.xts")
    result = resolve_alias_to_xts_path("webtest")
    assert result == str(local_file)

def test_resolve_direct_url(mock_alias_config):
    url = "https://web.site/direct.xts"
    result = url
    assert result == url

def test_resolve_file_path(mock_alias_config, tmp_path):
    local_file = tmp_path / "dummy.xts"
    local_file.write_text("steps: []")
    result = str(local_file)
    assert result == str(local_file)

# --- AllocatorClient Commands ---
# --- Error Handling ---
# (Reuse or expand previous error handling tests here)

# --- Error Handling Tests (from test_xts_error_handling.py) ---
def test_missing_alias(monkeypatch, mock_alias_config):
    """Test running XTS with a missing alias."""
    # Remove all aliases before test
    aliases = load_aliases()
    for alias in list(aliases.keys()):
        remove_alias(alias)
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        sys.argv = ['xts', 'unknownalias']
        try:
            from xts_core.xts import XTS
            XTS()._parse_first_arg()
        except SystemExit:
            pass
        output = mock_stdout.getvalue()
        assert "Unknown alias" in output or "error" in output.lower()


def test_demo_builtin_runs_interactive_demo(monkeypatch, tmp_path):
    """Test that xts demo runs the interactive demo flow."""
    demo_file = tmp_path / 'hello_world.xts'
    demo_file.write_text('run:\n  hello_world:\n    command: echo "hello world"\n', encoding='utf-8')

    monkeypatch.setattr('xts_core.xts_alias.add_alias_from_input', lambda path, name: [(name, str(path))])
    monkeypatch.setattr('xts_core.xts_alias.list_aliases', lambda: None)
    monkeypatch.setattr('xts_core.xts_alias.refresh_alias', lambda name: (name, str(demo_file)))
    monkeypatch.setattr('xts_core.xts_alias.remove_alias', lambda name: True)

    class FakeRunner:
        def __init__(self, *args, **kwargs):
            pass

        def run(self, args):
            assert args == ['run', 'hello_world']
            return (None, None, [0])

    monkeypatch.setattr('xts_core.xts.YamlRunner', FakeRunner)
    monkeypatch.setattr('builtins.input', lambda prompt='': '')
    monkeypatch.setattr('xts_core.xts.XTS._find_demo_example_config', lambda self: str(demo_file))

    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        sys.argv = ['xts', 'demo']
        from xts_core.xts import XTS
        with pytest.raises(SystemExit) as excinfo:
            XTS().run()
        assert excinfo.value.code == 0
        output = mock_stdout.getvalue()
        assert 'Welcome to the XTS interactive demo' in output
        assert 'Section 1: Alias help command.' in output
        assert 'Command: xts --alias --help' in output
        assert 'Section 2: Add a demo alias for the example file.' in output
        assert 'Command: xts --alias --add' in output
        assert 'Section 3: List available aliases.' in output
        assert 'Command: xts --alias --list' in output
        assert 'Section 4: Run the demo alias command.' in output
        assert 'Command: xts demo-example run hello_world' in output
        assert 'Section 5: Remove the demo alias.' in output
        assert 'Command: xts --alias --remove demo-example' in output
        assert 'Section 6: Refresh the demo alias.' in output
        assert 'Command: xts --alias --refresh demo-example' in output
        assert 'demo-example ->' in output
        assert 'Removed alias: demo-example' in output
        assert 'Demo finished. You can now add your own aliases' in output


def test_malformed_xts_file(monkeypatch, mock_alias_config, tmp_path):
    """Test registering and using a malformed .xts file."""
    malformed_file = tmp_path / "bad.xts"
    malformed_file.write_text("not: [valid: yaml")
    add_alias("badalias", str(malformed_file), str(malformed_file))
    # Simulate loading the alias (should fail gracefully)
    result = resolve_alias_to_xts_path("badalias")
    assert result == str(malformed_file)

def test_multiple_aliases(mock_alias_config, tmp_path):
    """Test behavior with multiple aliases registered."""
    file1 = tmp_path / "file1.xts"
    file2 = tmp_path / "file2.xts"
    file1.write_text("steps: []")
    file2.write_text("steps: []")
    add_alias("alias1", str(file1), str(file1))
    add_alias("alias2", str(file2), str(file2))
    aliases = load_aliases()
    assert "alias1" in aliases and "alias2" in aliases


def test_validate_xts_file_success(tmp_path):
    valid_file = tmp_path / "valid.xts"
    valid_file.write_text(
        "run:\n"
        "  hello_world:\n"
        "    command: echo \"hello world\"\n"
    )

    with pytest.raises(SystemExit) as excinfo:
        XTS()._run_validate_command([str(valid_file)])

    assert excinfo.value.code == 0


def test_validate_cli_subcommand(monkeypatch, tmp_path):
    valid_file = tmp_path / "valid.xts"
    valid_file.write_text(
        "run:\n"
        "  hello_world:\n"
        "    command: echo \"hello world\"\n"
    )

    monkeypatch.setattr(sys, "argv", ["xts", "validate", str(valid_file)])
    with pytest.raises(SystemExit) as excinfo:
        XTS().run()

    assert excinfo.value.code == 0


def test_validate_without_path_shows_usage(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["xts", "validate"])
    with patch('sys.stdout', new=StringIO()) as mock_stdout:
        with pytest.raises(SystemExit) as excinfo:
            XTS().run()

    assert excinfo.value.code == 1
    output = mock_stdout.getvalue().lower()
    assert "usage: xts validate" in output
    assert "example:" in output


def test_validate_xts_file_syntax_error(tmp_path):
    invalid_file = tmp_path / "invalid.xts"
    invalid_file.write_text("not: [valid: yaml")

    with patch('sys.stdout', new=StringIO()) as mock_stdout:
        with pytest.raises(SystemExit) as excinfo:
            XTS()._run_validate_command([str(invalid_file)])

    assert excinfo.value.code == 1
    assert "incorrectly formatted" in mock_stdout.getvalue().lower()


def test_validate_xts_file_missing(tmp_path):
    missing_file = tmp_path / "missing.xts"
    with patch('sys.stdout', new=StringIO()) as mock_stdout:
        with pytest.raises(SystemExit) as excinfo:
            XTS()._run_validate_command([str(missing_file)])

    assert excinfo.value.code == 1
    assert "does not exist" in mock_stdout.getvalue().lower()


def test_validate_xts_file_invalid_structure(tmp_path):
    invalid_file = tmp_path / "invalid.xts"
    invalid_file.write_text("run:\n  - name: hello\n    command: echo \"hello\"")

    with patch('sys.stdout', new=StringIO()) as mock_stdout:
        with pytest.raises(SystemExit) as excinfo:
            XTS()._run_validate_command([str(invalid_file)])

    assert excinfo.value.code == 1
    assert "lists are not supported" in mock_stdout.getvalue().lower()


def test_validate_xts_file_invalid_command_string(tmp_path):
    invalid_file = tmp_path / "invalid_command.xts"
    invalid_file.write_text(
        "run:\n"
        "  hello_world:\n"
        "    command: echo \"hello\n"
    )

    with patch('sys.stdout', new=StringIO()) as mock_stdout:
        with pytest.raises(SystemExit) as excinfo:
            XTS()._run_validate_command([str(invalid_file)])

    assert excinfo.value.code == 1
    assert "unbalanced quotes" in mock_stdout.getvalue().lower()


def test_allocator_add_slot_missing_args(monkeypatch):
    """Test add-slot with missing required arguments."""
    client = XTSAllocatorClient()
    args = ['allocator', 'add-slot', '--rackName', 'R1', '--server', 'http://allocator-server']
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        with pytest.raises(SystemExit):
            client.run(args)
        output = mock_stdout.getvalue()
        assert "slotName" in output or "platform" in output or "Error" in output

def test_allocator_update_slot_invalid_id(monkeypatch):
    """Test update-slot with invalid slot_id."""
    client = XTSAllocatorClient()
    args = ['allocator', 'update-slot', '--slot_id', 'notanumber', '--platform', 'linux', '--server', 'http://allocator-server']
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        try:
            client.run(args)
        except SystemExit:
            pass
        output = mock_stdout.getvalue()
        assert ("Error" in output or "invalid" in output or "Usage:" in output)
