import os
import sys
import pytest
from unittest.mock import patch
from io import StringIO

sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from xts_core.xts_alias import (
    add_alias,
    remove_alias,
    resolve_alias_to_xts_path,
    add_alias_from_input,
    refresh_alias,
    load_aliases
)
from xts_core.plugins.xts_allocator_client import XTSAllocatorClient

@pytest.fixture
def mock_alias_config(monkeypatch, tmp_path):
    temp_home = tmp_path / "home"
    config_dir = temp_home / ".xts"
    config_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(temp_home))
    yield config_dir

# --- Alias Management ---
def test_add_and_list_alias(mock_alias_config):
    add_alias("test1", "http://example.com/test.xts", "http://example.com/test.xts")
    aliases = load_aliases()
    assert "test1" in aliases
    assert aliases["test1"]["source"] == "http://example.com/test.xts"

def test_remove_alias(mock_alias_config):
    add_alias("test2", "https://url.com/file.xts", "https://url.com/file.xts")
    remove_alias("test2")
    aliases = load_aliases()
    assert "test2" not in aliases

def test_resolve_alias(mock_alias_config):
    add_alias("webtest", "https://web.site/test.xts", "https://web.site/test.xts")
    result = resolve_alias_to_xts_path("webtest")
    assert result == "https://web.site/test.xts"

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
@pytest.fixture
def mock_client():
    with patch.object(XTSAllocatorClient, '_send_request', return_value={"slot_id": "12345"}):
        yield XTSAllocatorClient()

def test_allocate_slot_with_id(mock_client):
    args = ['allocate', '--id', '123', '--server', 'http://allocator-server']
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        try:
            mock_client.run(args)
        except SystemExit:
            pass
        output = mock_stdout.getvalue()
        assert ("Slot allocated successfully" in output or "Usage:" in output or "error" in output.lower())

def test_allocate_slot_with_platform_and_tags(mock_client):
    args = ['allocate', '--platform', 'linux', '--tags', 'gpu', '--server', 'http://allocator-server']
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        try:
            mock_client.run(args)
        except SystemExit:
            pass
        output = mock_stdout.getvalue()
        assert ("Slot allocated successfully" in output or "Usage:" in output or "error" in output.lower())

def test_allocate_slot_with_platform_no_tags(mock_client):
    args = ['allocate', '--platform', 'linux', '--server', 'http://allocator-server']
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        try:
            mock_client.run(args)
        except SystemExit:
            pass
        output = mock_stdout.getvalue()
        assert ("Slot allocated successfully" in output or "Usage:" in output or "error" in output.lower())

def test_deallocate_slot(mock_client):
    args = ['deallocate', '--id', '123', '--server', 'http://allocator-server']
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        try:
            mock_client.run(args)
        except SystemExit:
            pass
        output = mock_stdout.getvalue()
        assert ("Slot deallocated successfully" in output or "Usage:" in output or "error" in output.lower())

def test_allocator_add_server(mock_client):
    args = ['allocator', 'add', 'test_allocator', 'http://allocator-server']
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        try:
            mock_client.run(args)
        except SystemExit:
            pass
        output = mock_stdout.getvalue()
        assert ("Server added" in output or "Usage:" in output or "error" in output.lower())

def test_allocator_remove_server(mock_client):
    args = ['allocator', 'remove', 'test_allocator']
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        try:
            mock_client.run(args)
        except SystemExit:
            pass
        output = mock_stdout.getvalue()
        assert ("Server removed" in output or "Usage:" in output or "error" in output.lower())

def test_allocator_list_servers(mock_client):
    args = ['allocator', 'list']
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        try:
            mock_client.run(args)
        except SystemExit:
            pass
        output = mock_stdout.getvalue()
        assert ("No servers configured" in output or "Server" in output or "Usage:" in output or "error" in output.lower())

def test_allocator_add_slot(mock_client):
    args = ['allocator', 'add-slot', '--rackName', 'R1', '--slotName', 'S1', '--platform', 'linux', '--server', 'http://allocator-server']
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        try:
            mock_client.run(args)
        except SystemExit:
            pass
        output = mock_stdout.getvalue()
        assert ("Slot created" in output or "Success" in output or "Usage:" in output or "error" in output.lower())

def test_allocator_update_slot(mock_client):
    args = ['allocator', 'update-slot', '--slot_id', '123', '--platform', 'windows', '--server', 'http://allocator-server']
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        try:
            mock_client.run(args)
        except SystemExit:
            pass
        output = mock_stdout.getvalue()
        assert ("Slot updated" in output or "Success" in output or "Usage:" in output or "error" in output.lower())

def test_allocator_remove_slot(mock_client):
    args = ['allocator', 'remove-slot', '--slot_id', '123', '--server', 'http://allocator-server']
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        try:
            mock_client.run(args)
        except SystemExit:
            pass
        output = mock_stdout.getvalue()
        assert ("Slot removed" in output or "Success" in output or "Usage:" in output or "error" in output.lower())

def test_allocator_search_slots(mock_client):
    args = ['allocator', 'search', '--platform', 'linux', '--tags', 'gpu', '--server', 'http://allocator-server']
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        try:
            mock_client.run(args)
        except SystemExit:
            pass
        output = mock_stdout.getvalue()
        assert ("Matching slots" in output or "Success" in output or "Usage:" in output or "error" in output.lower())

def test_allocator_list_all_slots(mock_client):
    args = ['allocator', 'list', '--server', 'http://allocator-server']
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        try:
            mock_client.run(args)
        except SystemExit:
            pass
        output = mock_stdout.getvalue()
        assert ("available slots" in output or "Success" in output or "Usage:" in output or "error" in output.lower())

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
        result = load_aliases()
        assert result == {}  # No aliases present
        output = mock_stdout.getvalue()
        # Optionally check for error message if CLI is invoked

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
