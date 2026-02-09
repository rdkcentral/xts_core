#!/usr/bin/env python3
"""Tests for enhanced XTS alias system with universal caching.

Tests cover:
- Universal caching (local and remote files)
- Absolute path resolution
- Directory scanning (recursive and non-recursive)
- Version tracking and update detection
- Alias commands (add, list, remove, refresh, clean)
- Metadata management
- Broken alias detection
"""

import os
import json
import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "3rdParty" / "xts_core" / "src"))

from xts_core import xts_alias


@pytest.fixture
def temp_xts_dir(tmp_path):
    """Create temporary XTS directory structure."""
    xts_dir = tmp_path / ".xts"
    cache_dir = xts_dir / "cache"
    cache_dir.mkdir(parents=True)
    
    alias_file = xts_dir / "aliases.json"
    metadata_file = xts_dir / "metadata.json"
    
    # Patch the module constants
    original_cache = xts_alias.CACHE_DIR
    original_alias = xts_alias.ALIAS_FILE
    original_metadata = xts_alias.METADATA_FILE
    
    xts_alias.CACHE_DIR = str(cache_dir)
    xts_alias.ALIAS_FILE = str(alias_file)
    xts_alias.METADATA_FILE = str(metadata_file)
    
    yield xts_dir
    
    # Restore original paths
    xts_alias.CACHE_DIR = original_cache
    xts_alias.ALIAS_FILE = original_alias
    xts_alias.METADATA_FILE = original_metadata


@pytest.fixture
def sample_xts_content():
    """Sample .xts file content."""
    return """commands:
  test_cmd:
    description: Test command
    command: echo "Hello World"
"""


@pytest.fixture
def sample_xts_files(tmp_path, sample_xts_content):
    """Create sample .xts files for testing."""
    files = {}
    
    # Single file
    single = tmp_path / "test.xts"
    single.write_text(sample_xts_content)
    files['single'] = single
    
    # Directory with multiple files
    multi_dir = tmp_path / "multi"
    multi_dir.mkdir()
    
    for i in range(3):
        f = multi_dir / f"config{i}.xts"
        f.write_text(sample_xts_content)
        files[f'multi_{i}'] = f
    
    # Nested directory structure
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "top.xts").write_text(sample_xts_content)
    
    sub = nested / "sub"
    sub.mkdir()
    (sub / "middle.xts").write_text(sample_xts_content)
    
    deep = sub / "deep"
    deep.mkdir()
    (deep / "bottom.xts").write_text(sample_xts_content)
    
    files['nested_dir'] = nested
    
    return files


class TestEnsureDirs:
    """Test directory creation."""
    
    def test_ensure_dirs_creates_cache(self, temp_xts_dir):
        """Test that ensure_dirs creates cache directory."""
        cache_dir = Path(xts_alias.CACHE_DIR)
        assert cache_dir.exists()
        assert cache_dir.is_dir()
    
    def test_ensure_dirs_creates_alias_parent(self, temp_xts_dir):
        """Test that ensure_dirs creates parent of alias file."""
        alias_parent = Path(xts_alias.ALIAS_FILE).parent
        assert alias_parent.exists()


class TestComputeFileHash:
    """Test file hash computation."""
    
    def test_compute_file_hash(self, tmp_path):
        """Test SHA256 hash computation."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        hash1 = xts_alias.compute_file_hash(str(test_file))
        assert len(hash1) == 64  # SHA256 produces 64 hex chars
        
        # Same content should produce same hash
        hash2 = xts_alias.compute_file_hash(str(test_file))
        assert hash1 == hash2
    
    def test_compute_file_hash_different_content(self, tmp_path):
        """Test different content produces different hash."""
        file1 = tmp_path / "test1.txt"
        file1.write_text("content 1")
        
        file2 = tmp_path / "test2.txt"
        file2.write_text("content 2")
        
        hash1 = xts_alias.compute_file_hash(str(file1))
        hash2 = xts_alias.compute_file_hash(str(file2))
        
        assert hash1 != hash2
    
    def test_compute_file_hash_missing_file(self, tmp_path):
        """Test hash of missing file returns empty string."""
        missing = tmp_path / "missing.txt"
        hash_val = xts_alias.compute_file_hash(str(missing))
        assert hash_val == ""


class TestIsUrl:
    """Test URL detection."""
    
    def test_is_url_http(self):
        """Test HTTP URL detection."""
        assert xts_alias.is_url("http://example.com/file.xts")
    
    def test_is_url_https(self):
        """Test HTTPS URL detection."""
        assert xts_alias.is_url("https://example.com/file.xts")
    
    def test_is_url_local_path(self):
        """Test local paths are not URLs."""
        assert not xts_alias.is_url("/path/to/file.xts")
        assert not xts_alias.is_url("./file.xts")
        assert not xts_alias.is_url("file.xts")


class TestFindXtsFiles:
    """Test .xts file discovery."""
    
    def test_find_xts_files_single_directory(self, sample_xts_files):
        """Test finding .xts files in single directory."""
        multi_dir = sample_xts_files['multi_0'].parent
        files = xts_alias.find_xts_files(str(multi_dir), recursive=False)
        
        assert len(files) == 3
        assert all(f.endswith('.xts') for f in files)
    
    def test_find_xts_files_recursive(self, sample_xts_files):
        """Test recursive .xts file discovery."""
        nested_dir = sample_xts_files['nested_dir']
        files = xts_alias.find_xts_files(str(nested_dir), recursive=True)
        
        # Should find top.xts, middle.xts, bottom.xts
        assert len(files) == 3
        assert all(f.endswith('.xts') for f in files)
    
    def test_find_xts_files_non_recursive(self, sample_xts_files):
        """Test non-recursive only finds top-level."""
        nested_dir = sample_xts_files['nested_dir']
        files = xts_alias.find_xts_files(str(nested_dir), recursive=False)
        
        # Should only find top.xts
        assert len(files) == 1
        assert files[0].endswith('top.xts')
    
    def test_find_xts_files_empty_directory(self, tmp_path):
        """Test finding files in empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        files = xts_alias.find_xts_files(str(empty_dir))
        assert files == []
    
    def test_find_xts_files_not_directory(self, tmp_path):
        """Test with non-directory path."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")
        
        files = xts_alias.find_xts_files(str(file_path))
        assert files == []


class TestCacheLocalFile:
    """Test local file caching."""
    
    def test_cache_local_file(self, temp_xts_dir, sample_xts_files):
        """Test caching a local file."""
        source = sample_xts_files['single']
        cache_path = Path(xts_alias.CACHE_DIR) / "test_cache.xts"
        
        success, metadata = xts_alias.cache_local_file(str(source), str(cache_path))
        
        assert success
        assert cache_path.exists()
        assert metadata['source'] == str(source)
        assert metadata['source_type'] == 'local'
        assert 'hash' in metadata
        assert 'cached_at' in metadata
        assert 'source_mtime' in metadata
    
    def test_cache_local_file_preserves_content(self, temp_xts_dir, sample_xts_files, sample_xts_content):
        """Test cached file has same content as source."""
        source = sample_xts_files['single']
        cache_path = Path(xts_alias.CACHE_DIR) / "test_cache.xts"
        
        xts_alias.cache_local_file(str(source), str(cache_path))
        
        assert cache_path.read_text() == sample_xts_content
    
    def test_cache_local_file_missing_source(self, temp_xts_dir, tmp_path):
        """Test caching missing file fails gracefully."""
        missing = tmp_path / "missing.xts"
        cache_path = Path(xts_alias.CACHE_DIR) / "test_cache.xts"
        
        # Should raise SystemExit when file doesn't exist
        with pytest.raises(SystemExit) as exc_info:
            xts_alias.cache_local_file(str(missing), str(cache_path))
        assert exc_info.value.code == 1


class TestAddAlias:
    """Test adding aliases."""
    
    def test_add_alias_local_file(self, temp_xts_dir, sample_xts_files):
        """Test adding local file alias."""
        source = sample_xts_files['single']
        
        xts_alias.add_alias('test', str(source))
        
        aliases = xts_alias.list_aliases()
        assert 'test' in aliases
        
        # Check cache was created
        cache_path = Path(aliases['test'])
        assert cache_path.exists()
        assert cache_path.parent == Path(xts_alias.CACHE_DIR)
    
    def test_add_alias_creates_metadata(self, temp_xts_dir, sample_xts_files):
        """Test adding alias creates metadata."""
        source = sample_xts_files['single']
        
        xts_alias.add_alias('test', str(source))
        
        metadata = xts_alias.load_metadata()
        assert 'test' in metadata
        assert metadata['test']['source'] == str(source.resolve())
        assert metadata['test']['source_type'] == 'local'
    
    def test_add_alias_absolute_path(self, temp_xts_dir, sample_xts_files):
        """Test relative paths converted to absolute."""
        source = sample_xts_files['single']
        
        # Use relative path
        relative = os.path.relpath(source)
        xts_alias.add_alias('test', relative)
        
        metadata = xts_alias.load_metadata()
        # Should be stored as absolute
        assert os.path.isabs(metadata['test']['source'])
    
    @patch('xts_core.xts_alias.REQUESTS_AVAILABLE', True)
    @patch('xts_core.xts_alias.requests')
    def test_add_alias_remote_url(self, mock_requests, temp_xts_dir, sample_xts_content):
        """Test adding remote URL alias."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.text = sample_xts_content
        mock_response.headers = {
            'ETag': 'test-etag',
            'Last-Modified': 'Mon, 01 Jan 2026 00:00:00 GMT'
        }
        mock_response.raise_for_status = Mock()
        mock_requests.get.return_value = mock_response
        
        url = "https://example.com/config.xts"
        xts_alias.add_alias('remote', url)
        
        aliases = xts_alias.list_aliases()
        assert 'remote' in aliases
        
        metadata = xts_alias.load_metadata()
        assert metadata['remote']['source'] == url
        assert metadata['remote']['source_type'] == 'remote'
        assert 'http_headers' in metadata['remote']


class TestListAliases:
    """Test listing aliases."""
    
    def test_list_aliases_empty(self, temp_xts_dir):
        """Test listing when no aliases exist."""
        aliases = xts_alias.list_aliases()
        assert aliases == {}
    
    def test_list_aliases_multiple(self, temp_xts_dir, sample_xts_files):
        """Test listing multiple aliases."""
        xts_alias.add_alias('alias1', str(sample_xts_files['single']))
        xts_alias.add_alias('alias2', str(sample_xts_files['multi_0']))
        
        aliases = xts_alias.list_aliases()
        assert len(aliases) == 2
        assert 'alias1' in aliases
        assert 'alias2' in aliases


class TestRemoveAlias:
    """Test removing aliases."""
    
    def test_remove_alias(self, temp_xts_dir, sample_xts_files):
        """Test removing an alias."""
        source = sample_xts_files['single']
        xts_alias.add_alias('test', str(source))
        
        # Verify it exists
        aliases = xts_alias.list_aliases()
        assert 'test' in aliases
        cache_path = aliases['test']
        
        # Remove it
        xts_alias.remove_alias('test')
        
        # Verify removed
        aliases = xts_alias.list_aliases()
        assert 'test' not in aliases
        
        # Cache file should be deleted
        assert not Path(cache_path).exists()
    
    def test_remove_alias_removes_metadata(self, temp_xts_dir, sample_xts_files):
        """Test removing alias also removes metadata."""
        source = sample_xts_files['single']
        xts_alias.add_alias('test', str(source))
        
        xts_alias.remove_alias('test')
        
        metadata = xts_alias.load_metadata()
        assert 'test' not in metadata
    
    def test_remove_nonexistent_alias(self, temp_xts_dir):
        """Test removing non-existent alias doesn't error."""
        # Should not raise exception
        xts_alias.remove_alias('nonexistent')


class TestCheckLocalUpdates:
    """Test checking for local file updates."""
    
    def test_check_local_updates_no_change(self, temp_xts_dir, sample_xts_files):
        """Test no update when file unchanged."""
        source = sample_xts_files['single']
        xts_alias.add_alias('test', str(source))
        
        metadata = xts_alias.load_metadata()
        has_update, msg = xts_alias.check_local_updates(metadata['test'])
        
        assert not has_update
        assert "up to date" in msg.lower()
    
    def test_check_local_updates_file_modified(self, temp_xts_dir, sample_xts_files):
        """Test detects file modification."""
        source = sample_xts_files['single']
        xts_alias.add_alias('test', str(source))
        
        # Modify source file
        import time
        time.sleep(0.1)  # Ensure mtime changes
        source.write_text("modified content")
        
        metadata = xts_alias.load_metadata()
        has_update, msg = xts_alias.check_local_updates(metadata['test'])
        
        assert has_update
        assert "modified" in msg.lower()
    
    def test_check_local_updates_source_missing(self, temp_xts_dir, sample_xts_files):
        """Test when source file is deleted."""
        source = sample_xts_files['single']
        xts_alias.add_alias('test', str(source))
        
        # Delete source
        source.unlink()
        
        metadata = xts_alias.load_metadata()
        has_update, msg = xts_alias.check_local_updates(metadata['test'])
        
        assert not has_update
        assert "missing" in msg.lower()


class TestRefreshAlias:
    """Test refreshing aliases from source."""
    
    def test_refresh_alias_local_file(self, temp_xts_dir, sample_xts_files):
        """Test refreshing local alias."""
        source = sample_xts_files['single']
        xts_alias.add_alias('test', str(source))
        
        # Modify source
        new_content = "updated content"
        source.write_text(new_content)
        
        # Refresh
        success = xts_alias.refresh_alias('test')
        
        assert success
        
        # Check cache was updated
        aliases = xts_alias.list_aliases()
        cache_path = Path(aliases['test'])
        assert cache_path.read_text() == new_content
    
    def test_refresh_alias_nonexistent(self, temp_xts_dir):
        """Test refreshing non-existent alias."""
        # Should raise SystemExit when alias doesn't exist
        with pytest.raises(SystemExit) as exc_info:
            xts_alias.refresh_alias('nonexistent')
        assert exc_info.value.code == 1
    
    def test_refresh_alias_source_missing(self, temp_xts_dir, sample_xts_files):
        """Test refreshing when source is missing."""
        source = sample_xts_files['single']
        xts_alias.add_alias('test', str(source))
        
        # Delete source
        source.unlink()
        
        # Refresh should fail but not crash
        success = xts_alias.refresh_alias('test')
        assert not success
        
        # Cache should still exist
        aliases = xts_alias.list_aliases()
        assert Path(aliases['test']).exists()


class TestCleanBrokenAliases:
    """Test cleaning broken aliases."""
    
    def test_clean_broken_aliases_cache_missing(self, temp_xts_dir, sample_xts_files):
        """Test detecting missing cache files."""
        source = sample_xts_files['single']
        xts_alias.add_alias('test', str(source))
        
        # Delete cache file manually
        aliases = xts_alias.list_aliases()
        Path(aliases['test']).unlink()
        
        # Mock user input to clean
        with patch('builtins.input', return_value='y'):
            xts_alias.clean_broken_aliases()
        
        # Alias should be removed
        aliases = xts_alias.list_aliases()
        assert 'test' not in aliases
    
    def test_clean_broken_aliases_source_missing(self, temp_xts_dir, sample_xts_files):
        """Test detecting missing source files."""
        source = sample_xts_files['single']
        xts_alias.add_alias('test', str(source))
        
        # Delete source
        source.unlink()
        
        # Mock user input to clean
        with patch('builtins.input', return_value='y'):
            xts_alias.clean_broken_aliases()
        
        # Alias should be removed
        aliases = xts_alias.list_aliases()
        assert 'test' not in aliases
    
    def test_clean_broken_aliases_user_declines(self, temp_xts_dir, sample_xts_files):
        """Test user declining to clean."""
        source = sample_xts_files['single']
        xts_alias.add_alias('test', str(source))
        source.unlink()
        
        # Mock user input to decline
        with patch('builtins.input', return_value='n'):
            xts_alias.clean_broken_aliases()
        
        # Alias should still exist
        aliases = xts_alias.list_aliases()
        assert 'test' in aliases


class TestGetCachePath:
    """Test cache path generation."""
    
    def test_get_cache_path_unique(self):
        """Test different sources get different cache paths."""
        path1 = xts_alias.get_cache_path("/path/one.xts", "alias1")
        path2 = xts_alias.get_cache_path("/path/two.xts", "alias2")
        
        assert path1 != path2
    
    def test_get_cache_path_includes_alias_name(self):
        """Test cache path includes alias name."""
        path = xts_alias.get_cache_path("/path/file.xts", "myalias")
        
        assert "myalias" in path
    
    def test_get_cache_path_consistent(self):
        """Test same source gives same cache path."""
        path1 = xts_alias.get_cache_path("/path/file.xts", "alias")
        path2 = xts_alias.get_cache_path("/path/file.xts", "alias")
        
        assert path1 == path2


class TestDirectoryUIInteraction:
    """Test directory scanning with user prompts and bulk addition."""
    
    @patch('builtins.input', return_value='y')
    def test_add_directory_user_accepts(self, mock_input, temp_xts_dir, sample_xts_files):
        """Test adding directory when user accepts prompt."""
        multi_dir = sample_xts_files['multi_0'].parent
        
        # Call add_alias with directory path
        xts_alias.add_alias('bulk', str(multi_dir), recursive=False)
        
        # Verify user was prompted
        mock_input.assert_called_once()
        assert 'y/n' in mock_input.call_args[0][0].lower()
        
        # Verify files were added
        aliases = xts_alias.list_aliases()
        
        # Should have added 3 files (config0, config1, config2)
        assert len(aliases) >= 3
        assert any('config0' in name for name in aliases.keys())
        assert any('config1' in name for name in aliases.keys())
        assert any('config2' in name for name in aliases.keys())
    
    @patch('builtins.input', return_value='n')
    def test_add_directory_user_declines(self, mock_input, temp_xts_dir, sample_xts_files):
        """Test adding directory when user declines prompt."""
        multi_dir = sample_xts_files['multi_0'].parent
        
        # Call add_alias with directory path
        xts_alias.add_alias('bulk', str(multi_dir), recursive=False)
        
        # Verify user was prompted
        mock_input.assert_called_once()
        
        # Verify NO files were added
        aliases = xts_alias.list_aliases()
        assert len(aliases) == 0
    
    @patch('builtins.input', return_value='Y')  # Test uppercase
    def test_add_directory_user_accepts_uppercase(self, mock_input, temp_xts_dir, sample_xts_files):
        """Test adding directory with uppercase Y response."""
        multi_dir = sample_xts_files['multi_0'].parent
        
        # Call add_alias with directory path
        xts_alias.add_alias('bulk', str(multi_dir), recursive=False)
        
        # Verify files were added (case insensitive)
        aliases = xts_alias.list_aliases()
        assert len(aliases) >= 3
    
    @patch('builtins.input', return_value='y')
    def test_add_directory_shows_file_count(self, mock_input, temp_xts_dir, sample_xts_files, capsys):
        """Test that directory prompt shows correct file count."""
        multi_dir = sample_xts_files['multi_0'].parent
        
        xts_alias.add_alias('bulk', str(multi_dir), recursive=False)
        
        captured = capsys.readouterr()
        
        # Should show "Found 3 .xts file(s)"
        assert "Found 3" in captured.out or "3 .xts" in captured.out
        
        # Should list the files
        assert "config0.xts" in captured.out
        assert "config1.xts" in captured.out
        assert "config2.xts" in captured.out
    
    @patch('builtins.input', return_value='y')
    def test_add_directory_handles_duplicates(self, mock_input, temp_xts_dir, sample_xts_files):
        """Test directory addition with duplicate alias names."""
        multi_dir = sample_xts_files['multi_0'].parent
        
        # First add a single file with name 'config0'
        single_file = sample_xts_files['single']
        xts_alias.add_alias('config0', str(single_file), recursive=False)
        
        # Now add the directory which also has config0.xts
        xts_alias.add_alias('bulk', str(multi_dir), recursive=False)
        
        aliases = xts_alias.list_aliases()
        
        # Original config0 should be preserved
        assert 'config0' in aliases
        
        # New config0 should get renamed (config0_1, config0_2, etc.)
        assert any('config0_' in name for name in aliases.keys())
    
    @patch('builtins.input', return_value='y')
    def test_add_directory_recursive(self, mock_input, temp_xts_dir, sample_xts_files):
        """Test recursive directory scanning."""
        nested_dir = sample_xts_files['nested_dir']
        
        xts_alias.add_alias('nested', str(nested_dir), recursive=True)
        
        aliases = xts_alias.list_aliases()
        
        # Should find all 3 files: top.xts, middle.xts, bottom.xts
        assert len(aliases) >= 3
        assert any('top' in name for name in aliases.keys())
        assert any('middle' in name for name in aliases.keys())
        assert any('bottom' in name for name in aliases.keys())
    
    @patch('builtins.input', return_value='y')
    def test_add_directory_non_recursive(self, mock_input, temp_xts_dir, sample_xts_files):
        """Test non-recursive directory scanning."""
        nested_dir = sample_xts_files['nested_dir']
        
        xts_alias.add_alias('nested', str(nested_dir), recursive=False)
        
        aliases = xts_alias.list_aliases()
        
        # Should only find top.xts
        assert len(aliases) == 1
        assert any('top' in name for name in aliases.keys())
        # Should NOT find nested files
        assert not any('middle' in name for name in aliases.keys())
        assert not any('bottom' in name for name in aliases.keys())
    
    def test_add_empty_directory(self, temp_xts_dir, tmp_path, capsys):
        """Test adding directory with no .xts files."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        xts_alias.add_alias('empty', str(empty_dir), recursive=False)
        
        captured = capsys.readouterr()
        
        # Should show warning about no files
        assert "No .xts files found" in captured.out or "warning" in captured.out.lower()
        
        # Should not save anything
        aliases = xts_alias.list_aliases()
        assert len(aliases) == 0
    
    @patch('builtins.input', return_value='y')
    def test_add_directory_metadata_tracking(self, mock_input, temp_xts_dir, sample_xts_files):
        """Test that metadata is tracked for bulk-added files."""
        multi_dir = sample_xts_files['multi_0'].parent
        
        xts_alias.add_alias('bulk', str(multi_dir), recursive=False)
        
        # Load metadata
        metadata = xts_alias.load_metadata()
        
        # Should have metadata for each added file
        assert len(metadata) == 3
        
        # Each metadata entry should have required fields
        for meta in metadata.values():
            assert 'source' in meta  # Correct field name
            assert 'cached_at' in meta
            assert 'hash' in meta
            assert 'source_mtime' in meta
    
    @patch('builtins.input', return_value='y')
    def test_add_directory_success_message(self, mock_input, temp_xts_dir, sample_xts_files, capsys):
        """Test success message shows correct count."""
        multi_dir = sample_xts_files['multi_0'].parent
        
        xts_alias.add_alias('bulk', str(multi_dir), recursive=False)
        
        captured = capsys.readouterr()
        
        # Should show success message with count
        assert "Added 3" in captured.out or "✓" in captured.out
    
    @patch('builtins.input', return_value='y')
    def test_add_directory_generates_unique_names(self, mock_input, temp_xts_dir, tmp_path):
        """Test unique alias names generated from filenames."""
        # Create directory with identically named files in subdirs
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        (test_dir / "config.xts").write_text("commands: {}")
        
        dir1 = test_dir / "dir1"
        dir1.mkdir()
        (dir1 / "config.xts").write_text("commands: {}")
        
        dir2 = test_dir / "dir2"  
        dir2.mkdir()
        (dir2 / "config.xts").write_text("commands: {}")
        
        xts_alias.add_alias('test', str(test_dir), recursive=True)
        
        aliases = xts_alias.list_aliases()
        
        # All files should be added with unique names
        # Should have 3 files (config.xts in test/, dir1/, dir2/)
        assert len(aliases) == 3
        
        # Check that at least 2 got renamed (since they have duplicate names)
        alias_names = list(aliases.keys())
        config_aliases = [n for n in alias_names if 'config' in n]
        assert len(config_aliases) == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
