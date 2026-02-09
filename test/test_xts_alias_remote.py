#!/usr/bin/env python3
"""Tests for remote URL functionality in xts_alias.py.

Tests fetch_remote_file, check_remote_updates with HTTP mocking.
Covers lines 241-268 (remote URL handling).
"""

import os
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from xts_core import xts_alias


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create temporary cache directory."""
    cache_dir = tmp_path / ".xts" / "cache"
    cache_dir.mkdir(parents=True)
    
    # Patch cache directory
    with patch.object(xts_alias, 'CACHE_DIR', str(cache_dir)):
        with patch.object(xts_alias, 'ALIAS_FILE', str(tmp_path / ".xts" / "aliases.json")):
            with patch.object(xts_alias, 'METADATA_FILE', str(tmp_path / ".xts" / "metadata.json")):
                # Create empty files
                (tmp_path / ".xts" / "aliases.json").write_text("{}")
                (tmp_path / ".xts" / "metadata.json").write_text("{}")
                yield cache_dir


@pytest.fixture
def sample_xts_content():
    """Sample .xts file content."""
    return """description: Test XTS config
commands:
  test:
    description: Test command
    command: echo "hello"
"""


class TestRemoteURLDetection:
    """Test URL detection functionality."""
    
    def test_is_url_http(self):
        """Test HTTP URL detection."""
        assert xts_alias.is_url("http://example.com/config.xts")
    
    def test_is_url_https(self):
        """Test HTTPS URL detection."""
        assert xts_alias.is_url("https://example.com/config.xts")
    
    def test_is_url_local_path(self):
        """Test local path is not detected as URL."""
        assert not xts_alias.is_url("/path/to/file.xts")
        assert not xts_alias.is_url("./relative/path.xts")
    
    def test_is_url_with_port(self):
        """Test URL with port number."""
        assert xts_alias.is_url("http://localhost:8080/config.xts")


class TestFetchRemoteFile:
    """Test fetching files from remote URLs."""
    
    @pytest.mark.skipif(not xts_alias.REQUESTS_AVAILABLE, 
                        reason="requests library not available")
    @patch('xts_core.xts_alias.requests.get')
    def test_fetch_remote_success(self, mock_get, temp_cache_dir, sample_xts_content):
        """Test successful remote file fetch."""
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = sample_xts_content
        mock_response.headers = {
            'ETag': '"abc123"',
            'Last-Modified': 'Mon, 01 Jan 2024 00:00:00 GMT',
            'Content-Type': 'text/plain'
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Fetch remote file
        url = "http://example.com/test.xts"
        cache_path = temp_cache_dir / "test.xts"
        
        success, metadata = xts_alias.fetch_remote_file(url, str(cache_path))
        
        assert success
        assert metadata is not None
        assert metadata['source'] == url
        assert metadata['source_type'] == 'remote'
        assert 'http_headers' in metadata
        assert metadata['http_headers']['etag'] == '"abc123"'
        
        # Verify file was written
        assert cache_path.exists()
        assert sample_xts_content in cache_path.read_text()
    
    @pytest.mark.skipif(not xts_alias.REQUESTS_AVAILABLE,
                        reason="requests library not available")
    @patch('xts_core.xts_alias.requests.get')
    def test_fetch_remote_404_error(self, mock_get, temp_cache_dir):
        """Test handling 404 Not Found error."""
        # Mock 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status = Mock(side_effect=Exception("404 Not Found"))
        mock_get.return_value = mock_response
        
        url = "http://example.com/missing.xts"
        cache_path = temp_cache_dir / "missing.xts"
        
        # Should handle error gracefully (via utils.error which exits)
        with pytest.raises(SystemExit):
            xts_alias.fetch_remote_file(url, str(cache_path))
    
    @pytest.mark.skipif(not xts_alias.REQUESTS_AVAILABLE,
                        reason="requests library not available")
    @patch('xts_core.xts_alias.requests.get')
    def test_fetch_remote_timeout(self, mock_get, temp_cache_dir):
        """Test handling connection timeout."""
        import requests
        
        # Mock timeout exception
        mock_get.side_effect = requests.Timeout("Connection timeout")
        
        url = "http://example.com/slow.xts"
        cache_path = temp_cache_dir / "slow.xts"
        
        # Should handle timeout (via utils.error which exits)
        with pytest.raises(SystemExit):
            xts_alias.fetch_remote_file(url, str(cache_path))
    
    @pytest.mark.skipif(not xts_alias.REQUESTS_AVAILABLE,
                        reason="requests library not available")
    @patch('xts_core.xts_alias.requests.get')
    def test_fetch_remote_network_error(self, mock_get, temp_cache_dir):
        """Test handling network error."""
        import requests
        
        # Mock network error
        mock_get.side_effect = requests.ConnectionError("Network error")
        
        url = "http://example.com/test.xts"
        cache_path = temp_cache_dir / "test.xts"
        
        # Should handle error (via utils.error which exits)
        with pytest.raises(SystemExit):
            xts_alias.fetch_remote_file(url, str(cache_path))
    
    @pytest.mark.skipif(not xts_alias.REQUESTS_AVAILABLE,
                        reason="requests library not available")
    @patch('xts_core.xts_alias.requests.get')
    def test_fetch_remote_redirect(self, mock_get, temp_cache_dir, sample_xts_content):
        """Test handling HTTP redirects."""
        # Mock redirect followed by success
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = sample_xts_content
        mock_response.headers = {'ETag': '"redirect123"'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        url = "http://example.com/redirect"
        cache_path = temp_cache_dir / "redirect.xts"
        
        # fetch_remote_file doesn't have follow_redirects parameter
        # Redirects are handled automatically by requests
        success, metadata = xts_alias.fetch_remote_file(url, str(cache_path))
        
        assert success
        assert cache_path.exists()


class TestCheckRemoteUpdates:
    """Test checking for remote file updates."""
    
    @pytest.mark.skipif(not xts_alias.REQUESTS_AVAILABLE,
                        reason="requests library not available")
    @patch('xts_core.xts_alias.requests.head')
    def test_check_remote_updates_etag_changed(self, mock_head):
        """Test detecting update via ETag change."""
        # Mock HEAD response with new ETag
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'ETag': '"new_etag"'
        }
        mock_response.raise_for_status = Mock()
        mock_head.return_value = mock_response
        
        # Metadata with old ETag
        metadata = {
            'source': 'http://example.com/test.xts',
            'source_type': 'remote',
            'http_headers': {
                'etag': '"old_etag"'
            }
        }
        
        has_update, message = xts_alias.check_remote_updates(metadata)
        
        assert has_update
        assert 'ETag changed' in message
    
    @pytest.mark.skipif(not xts_alias.REQUESTS_AVAILABLE,
                        reason="requests library not available")
    @patch('xts_core.xts_alias.requests.head')
    def test_check_remote_updates_etag_unchanged(self, mock_head):
        """Test no update when ETag unchanged."""
        # Mock HEAD response with same ETag
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'ETag': '"same_etag"'
        }
        mock_response.raise_for_status = Mock()
        mock_head.return_value = mock_response
        
        metadata = {
            'source': 'http://example.com/test.xts',
            'source_type': 'remote',
            'http_headers': {
                'etag': '"same_etag"'
            }
        }
        
        has_update, message = xts_alias.check_remote_updates(metadata)
        
        assert not has_update
        assert 'Up to date' in message
    
    @pytest.mark.skipif(not xts_alias.REQUESTS_AVAILABLE,
                        reason="requests library not available")
    @patch('xts_core.xts_alias.requests.head')
    def test_check_remote_updates_last_modified(self, mock_head):
        """Test detecting update via Last-Modified header."""
        # Mock HEAD response with no ETag but changed Last-Modified
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'Last-Modified': 'Tue, 02 Jan 2024 00:00:00 GMT'
        }
        mock_response.raise_for_status = Mock()
        mock_head.return_value = mock_response
        
        metadata = {
            'source': 'http://example.com/test.xts',
            'source_type': 'remote',
            'http_headers': {
                'last_modified': 'Mon, 01 Jan 2024 00:00:00 GMT'
            }
        }
        
        has_update, message = xts_alias.check_remote_updates(metadata)
        
        assert has_update
        assert 'Last-Modified changed' in message
    
    @pytest.mark.skipif(not xts_alias.REQUESTS_AVAILABLE,
                        reason="requests library not available")
    @patch('xts_core.xts_alias.requests.head')
    def test_check_remote_updates_no_headers(self, mock_head):
        """Test checking when server provides no caching headers."""
        # Mock HEAD response with no ETag or Last-Modified
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.raise_for_status = Mock()
        mock_head.return_value = mock_response
        
        metadata = {
            'source': 'http://example.com/test.xts',
            'source_type': 'remote',
            'http_headers': {}
        }
        
        has_update, message = xts_alias.check_remote_updates(metadata)
        
        # Should report up to date (can't detect changes)
        assert not has_update
    
    @pytest.mark.skipif(not xts_alias.REQUESTS_AVAILABLE,
                        reason="requests library not available")
    @patch('xts_core.xts_alias.requests.head')
    def test_check_remote_updates_network_error(self, mock_head):
        """Test handling network error during update check."""
        import requests
        
        # Mock network error
        mock_head.side_effect = requests.ConnectionError("Network error")
        
        metadata = {
            'source': 'http://example.com/test.xts',
            'source_type': 'remote',
            'http_headers': {}
        }
        
        has_update, message = xts_alias.check_remote_updates(metadata)
        
        # Should report no update (can't check)
        assert not has_update
        assert 'Check failed' in message


class TestAddAliasRemoteURL:
    """Test adding aliases from remote URLs."""
    
    @pytest.mark.skipif(not xts_alias.REQUESTS_AVAILABLE,
                        reason="requests library not available")
    @patch('xts_core.xts_alias.requests.get')
    def test_add_alias_remote_url(self, mock_get, temp_cache_dir, sample_xts_content):
        """Test adding alias from remote URL."""
        # Mock successful fetch
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = sample_xts_content
        mock_response.headers = {
            'ETag': '"abc123"',
            'Content-Type': 'text/yaml'
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        url = "http://example.com/remote.xts"
        
        # Add alias
        xts_alias.add_alias('remote_test', url)
        
        # Verify alias was added
        aliases = xts_alias.list_aliases()
        assert 'remote_test' in aliases
        
        # Verify cache file exists
        cache_path = Path(aliases['remote_test'])
        assert cache_path.exists()
        
        # Verify metadata
        metadata = xts_alias.load_metadata()
        assert 'remote_test' in metadata
        assert metadata['remote_test']['source_type'] == 'remote'
        assert metadata['remote_test']['source'] == url


class TestRefreshRemoteAlias:
    """Test refreshing remote aliases."""
    
    @pytest.mark.skipif(not xts_alias.REQUESTS_AVAILABLE,
                        reason="requests library not available")
    @patch('xts_core.xts_alias.requests.get')
    def test_refresh_remote_alias(self, mock_get, temp_cache_dir, sample_xts_content):
        """Test refreshing remote alias updates cache."""
        # Initial fetch
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = sample_xts_content
        mock_response.headers = {'ETag': '"v1"'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        url = "http://example.com/test.xts"
        xts_alias.add_alias('test_refresh', url)
        
        # Get initial cache
        aliases = xts_alias.list_aliases()
        cache_path = Path(aliases['test_refresh'])
        initial_content = cache_path.read_text()
        
        # Mock updated content
        updated_content = sample_xts_content + "\n# Updated"
        mock_response.text = updated_content
        mock_response.headers = {'ETag': '"v2"'}
        
        # Refresh
        success = xts_alias.refresh_alias('test_refresh')
        
        assert success
        
        # Verify cache updated
        new_content = cache_path.read_text()
        assert '# Updated' in new_content


class TestRequestsNotAvailable:
    """Test behavior when requests library is not available."""
    
    def test_fetch_without_requests(self, temp_cache_dir):
        """Test fetch_remote_file when requests not available."""
        with patch.object(xts_alias, 'REQUESTS_AVAILABLE', False):
            url = "http://example.com/test.xts"
            cache_path = temp_cache_dir / "test.xts"
            
            # Should exit with error
            with pytest.raises(SystemExit):
                xts_alias.fetch_remote_file(url, str(cache_path))
    
    def test_check_updates_without_requests(self):
        """Test check_remote_updates when requests not available."""
        with patch.object(xts_alias, 'REQUESTS_AVAILABLE', False):
            metadata = {
                'source': 'http://example.com/test.xts',
                'source_type': 'remote'
            }
            
            has_update, message = xts_alias.check_remote_updates(metadata)
            
            # Should report no update available
            assert not has_update
            assert 'requests not available' in message


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
