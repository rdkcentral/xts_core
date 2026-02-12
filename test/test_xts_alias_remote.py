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


class TestProxySupport:
    """Test proxy configuration support for remote aliases."""
    
    def test_add_list_remove_proxy(self):
        """Test proxy management operations (add, list, remove)."""
        # Add proxies with different types
        xts_alias.add_proxy('test_proxy1', 'proxy1.example.com:8080', proxy_type='http')
        xts_alias.add_proxy('test_proxy2', 'proxy2.example.com:3128', proxy_type='https',
                           username='user1', password='secret123')
        xts_alias.add_proxy('test_proxy3', 'localhost:1080', proxy_type='socks5',
                           username='sockuser', password='sockpass')
        
        # List proxies
        proxies = xts_alias.list_proxies()
        assert 'test_proxy1' in proxies
        assert 'test_proxy2' in proxies
        assert 'test_proxy3' in proxies
        assert proxies['test_proxy1']['proxy'] == 'proxy1.example.com:8080'
        assert proxies['test_proxy1']['type'] == 'http'
        assert proxies['test_proxy2']['username'] == 'user1'
        assert proxies['test_proxy2']['type'] == 'https'
        assert proxies['test_proxy3']['type'] == 'socks5'
        
        # Get proxy config
        config1 = xts_alias.get_proxy_config('test_proxy1')
        assert config1 is not None
        assert config1['proxy'] == 'proxy1.example.com:8080'
        assert config1['type'] == 'http'
        
        # Remove proxy
        xts_alias.remove_proxy('test_proxy1')
        proxies = xts_alias.list_proxies()
        assert 'test_proxy1' not in proxies
        assert 'test_proxy2' in proxies
        
        # Cleanup
        xts_alias.remove_proxy('test_proxy2')
        xts_alias.remove_proxy('test_proxy3')
    
    @pytest.mark.skipif(not xts_alias.REQUESTS_AVAILABLE, 
                        reason="requests library not available")
    @patch('xts_core.xts_alias.requests.get')
    def test_fetch_with_proxy(self, mock_get, temp_cache_dir, sample_xts_content):
        """Test fetching remote file with proxy configuration."""
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = sample_xts_content
        mock_response.headers = {
            'ETag': '"proxy123"',
            'Last-Modified': 'Mon, 01 Jan 2024 00:00:00 GMT',
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Fetch with proxy config
        url = "http://example.com/test.xts"
        cache_path = temp_cache_dir / "test.xts"
        proxy_config = {
            'proxy': 'proxy.example.com:8080',
            'type': 'http',
            'username': None,
            'password': None
        }
        
        success, metadata = xts_alias.fetch_remote_file(url, str(cache_path), proxy_config)
        
        assert success
        assert metadata is not None
        
        # Verify requests.get was called with proxies
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert 'proxies' in call_kwargs
        assert call_kwargs['proxies'] is not None
    
    @pytest.mark.skipif(not xts_alias.REQUESTS_AVAILABLE, 
                        reason="requests library not available")
    @patch('xts_core.xts_alias.requests.get')
    def test_fetch_with_proxy_auth(self, mock_get, temp_cache_dir, sample_xts_content):
        """Test fetching remote file with proxy authentication."""
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = sample_xts_content
        mock_response.headers = {'ETag': '"auth123"'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Fetch with proxy config including auth
        url = "http://example.com/test.xts"
        cache_path = temp_cache_dir / "test.xts"
        proxy_config = {
            'proxy': 'proxy.example.com:8080',
            'type': 'http',
            'username': 'user1',
            'password': 'pass123'
        }
        
        success, metadata = xts_alias.fetch_remote_file(url, str(cache_path), proxy_config)
        
        assert success
        
        # Verify requests.get was called with proxies containing credentials
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert 'proxies' in call_kwargs
        proxies = call_kwargs['proxies']
        
        # Credentials should be embedded in proxy URL
        assert 'user1:pass123@' in proxies['http']
        assert 'proxy.example.com:8080' in proxies['http']
    
    @pytest.mark.skipif(not xts_alias.REQUESTS_AVAILABLE, 
                        reason="requests library not available")
    @patch('xts_core.xts_alias.requests.get')
    def test_add_alias_with_proxy(self, mock_get, temp_cache_dir, sample_xts_content):
        """Test add_alias with proxy reference (new design)."""
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = sample_xts_content
        mock_response.headers = {'ETag': '"xyz789"'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # First, create a proxy
        xts_alias.add_proxy('myproxy', 'proxy.example.com:8080', proxy_type='http',
                           username='user1', password='secret')
        
        # Add alias with proxy reference
        url = "http://example.com/test.xts"
        xts_alias.add_alias('test_proxy', url, proxy_name='myproxy')
        
        # Verify alias was added
        aliases = xts_alias.list_aliases()
        assert 'test_proxy' in aliases
        
        # Verify metadata contains proxy_name reference
        metadata = xts_alias.load_metadata()
        assert 'test_proxy' in metadata
        assert 'proxy_name' in metadata['test_proxy']
        assert metadata['test_proxy']['proxy_name'] == 'myproxy'
        
        # Cleanup
        xts_alias.remove_proxy('myproxy')
    
    @pytest.mark.skipif(not xts_alias.REQUESTS_AVAILABLE, 
                        reason="requests library not available")
    @patch('xts_core.xts_alias.requests.head')
    def test_check_updates_with_proxy(self, mock_head):
        """Test checking for updates with proxy name reference."""
        # Create a proxy
        xts_alias.add_proxy('update_proxy', 'proxy.example.com:8080', proxy_type='https',
                           username='user1', password='secret')
        
        # Mock HEAD response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'ETag': '"new123"'}
        mock_response.raise_for_status = Mock()
        mock_head.return_value = mock_response
        
        # Metadata with proxy_name reference
        metadata = {
            'source': 'http://example.com/test.xts',
            'source_type': 'remote',
            'http_headers': {'etag': '"old123"'},
            'proxy_name': 'update_proxy'
        }
        
        has_update, message = xts_alias.check_remote_updates(metadata)
        
        # Should detect update based on ETag change
        assert has_update
        
        # Verify HEAD request was made with proxies
        mock_head.assert_called_once()
        call_kwargs = mock_head.call_args[1]
        assert 'proxies' in call_kwargs
        assert call_kwargs['proxies'] is not None
        
        # Cleanup
        xts_alias.remove_proxy('update_proxy')


class TestProxyFeature:
    """Comprehensive tests for proxy configuration and usage."""
    
    def test_add_http_proxy(self):
        """Test adding HTTP proxy configuration."""
        # Add HTTP proxy
        success = xts_alias.add_proxy('http_proxy', 'proxy.example.com:8080', 
                                     proxy_type='http')
        assert success
        
        # Verify proxy was saved
        proxies = xts_alias.load_proxies()
        assert 'http_proxy' in proxies
        assert proxies['http_proxy']['proxy'] == 'proxy.example.com:8080'
        assert proxies['http_proxy']['type'] == 'http'
        
        # Cleanup
        xts_alias.remove_proxy('http_proxy')
    
    def test_add_socks5_proxy(self):
        """Test adding SOCKS5 proxy configuration."""
        success = xts_alias.add_proxy('socks_proxy', 'socks.example.com:1080', 
                                     proxy_type='socks5')
        assert success
        
        proxies = xts_alias.load_proxies()
        assert 'socks_proxy' in proxies
        assert proxies['socks_proxy']['type'] == 'socks5'
        
        xts_alias.remove_proxy('socks_proxy')
    
    def test_add_proxy_with_credentials(self):
        """Test adding proxy with username and password."""
        success = xts_alias.add_proxy('auth_proxy', 'proxy.example.com:8080',
                                     username='testuser', password='testpass')
        assert success
        
        proxies = xts_alias.load_proxies()
        assert 'auth_proxy' in proxies
        assert proxies['auth_proxy']['username'] == 'testuser'
        assert proxies['auth_proxy']['password'] == 'testpass'
        
        xts_alias.remove_proxy('auth_proxy')
    
    def test_add_ssh_proxy(self):
        """Test adding SSH proxy configuration."""
        success = xts_alias.add_proxy('ssh_proxy', 'user@ssh.example.com:22',
                                     proxy_type='ssh')
        assert success
        
        proxies = xts_alias.load_proxies()
        assert 'ssh_proxy' in proxies
        assert proxies['ssh_proxy']['type'] == 'ssh'
        
        xts_alias.remove_proxy('ssh_proxy')
    
    def test_list_proxies(self):
        """Test listing configured proxies."""
        # Add multiple proxies
        xts_alias.add_proxy('proxy1', 'proxy1.example.com:8080')
        xts_alias.add_proxy('proxy2', 'proxy2.example.com:3128')
        
        proxies = xts_alias.list_proxies()
        
        assert 'proxy1' in proxies
        assert 'proxy2' in proxies
        assert len(proxies) >= 2
        
        # Cleanup
        xts_alias.remove_proxy('proxy1')
        xts_alias.remove_proxy('proxy2')
    
    def test_remove_proxy(self):
        """Test removing proxy configuration."""
        xts_alias.add_proxy('temp_proxy', 'temp.example.com:8080')
        
        # Verify it exists
        proxies = xts_alias.load_proxies()
        assert 'temp_proxy' in proxies
        
        # Remove it
        success = xts_alias.remove_proxy('temp_proxy')
        assert success
        
        # Verify it's gone
        proxies = xts_alias.load_proxies()
        assert 'temp_proxy' not in proxies
    
    def test_remove_nonexistent_proxy(self):
        """Test removing a proxy that doesn't exist."""
        success = xts_alias.remove_proxy('nonexistent_proxy')
        assert not success
    
    @pytest.mark.skipif(not xts_alias.REQUESTS_AVAILABLE, 
                        reason="requests library not available")
    @patch('xts_core.xts_alias.requests.get')
    def test_fetch_with_http_proxy(self, mock_get, temp_cache_dir, sample_xts_content):
        """Test fetching remote file through HTTP proxy."""
        # Configure HTTP proxy
        proxy_config = {
            'proxy': 'proxy.example.com:8080',
            'type': 'http'
        }
        
        # Mock successful fetch
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = sample_xts_content
        mock_response.headers = {'ETag': '"abc123"', 'Last-Modified': 'Wed, 21 Oct 2015 07:28:00 GMT'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        url = 'http://example.com/test.xts'
        cache_path = str(temp_cache_dir / 'test.xts')
        
        success, metadata = xts_alias.fetch_remote_file(url, cache_path, proxy_config)
        
        assert success
        assert metadata is not None
        
        # Verify proxy was used in request
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert 'proxies' in call_kwargs
        assert call_kwargs['proxies']['http'] == 'http://proxy.example.com:8080'
        assert call_kwargs['proxies']['https'] == 'http://proxy.example.com:8080'
    
    @pytest.mark.skipif(not xts_alias.REQUESTS_AVAILABLE, 
                        reason="requests library not available")
    @patch('xts_core.xts_alias.requests.get')
    def test_fetch_with_socks5_proxy(self, mock_get, temp_cache_dir, sample_xts_content):
        """Test fetching remote file through SOCKS5 proxy."""
        proxy_config = {
            'proxy': 'localhost:1080',
            'type': 'socks5'
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = sample_xts_content
        mock_response.headers = {}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        url = 'http://example.com/test.xts'
        cache_path = str(temp_cache_dir / 'test.xts')
        
        success, metadata = xts_alias.fetch_remote_file(url, cache_path, proxy_config)
        
        assert success
        
        # Verify SOCKS5 proxy URL format
        call_kwargs = mock_get.call_args[1]
        assert 'proxies' in call_kwargs
        assert call_kwargs['proxies']['http'].startswith('socks5://')
    
    @pytest.mark.skipif(not xts_alias.REQUESTS_AVAILABLE, 
                        reason="requests library not available")
    @patch('xts_core.xts_alias.requests.get')
    def test_fetch_with_authenticated_proxy(self, mock_get, temp_cache_dir, sample_xts_content):
        """Test fetching through proxy with authentication."""
        proxy_config = {
            'proxy': 'proxy.example.com:8080',
            'type': 'http',
            'username': 'proxyuser',
            'password': 'proxypass'
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = sample_xts_content
        mock_response.headers = {}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        url = 'http://example.com/test.xts'
        cache_path = str(temp_cache_dir / 'test.xts')
        
        success, metadata = xts_alias.fetch_remote_file(url, cache_path, proxy_config)
        
        assert success
        
        # Verify credentials were embedded in proxy URL
        call_kwargs = mock_get.call_args[1]
        proxy_url = call_kwargs['proxies']['http']
        assert 'proxyuser' in proxy_url
        assert 'proxypass' in proxy_url
        assert '@proxy.example.com:8080' in proxy_url
    
    @pytest.mark.skipif(not xts_alias.REQUESTS_AVAILABLE, 
                        reason="requests library not available")
    def test_fetch_with_ssh_proxy_returns_error(self, temp_cache_dir):
        """Test that SSH proxy returns error (not supported directly)."""
        proxy_config = {
            'proxy': 'user@ssh.example.com:22',
            'type': 'ssh'
        }
        
        url = 'http://example.com/test.xts'
        cache_path = str(temp_cache_dir / 'test.xts')
        
        success, metadata = xts_alias.fetch_remote_file(url, cache_path, proxy_config)
        
        # Should fail with SSH proxy (requires manual tunnel setup)
        assert not success
        assert metadata is None
    
    @pytest.mark.skipif(not xts_alias.REQUESTS_AVAILABLE, 
                        reason="requests library not available")
    @patch('xts_core.xts_alias.requests.get')
    def test_fetch_without_proxy(self, mock_get, temp_cache_dir, sample_xts_content):
        """Test fetching without proxy (baseline test)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = sample_xts_content
        mock_response.headers = {}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        url = 'http://example.com/test.xts'
        cache_path = str(temp_cache_dir / 'test.xts')
        
        success, metadata = xts_alias.fetch_remote_file(url, cache_path, proxy_config=None)
        
        assert success
        
        # Verify no proxy was used
        call_kwargs = mock_get.call_args[1]
        proxies = call_kwargs.get('proxies')
        assert proxies is None
    
    @pytest.mark.skipif(not xts_alias.REQUESTS_AVAILABLE, 
                        reason="requests library not available")
    @patch('xts_core.xts_alias.requests.get')
    def test_fetch_proxy_without_scheme(self, mock_get, temp_cache_dir, sample_xts_content):
        """Test proxy URL gets scheme added if missing."""
        proxy_config = {
            'proxy': 'proxy.example.com:8080',  # No scheme
            'type': 'http'
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = sample_xts_content
        mock_response.headers = {}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        url = 'http://example.com/test.xts'
        cache_path = str(temp_cache_dir / 'test.xts')
        
        success, metadata = xts_alias.fetch_remote_file(url, cache_path, proxy_config)
        
        assert success
        
        # Verify scheme was added
        call_kwargs = mock_get.call_args[1]
        proxy_url = call_kwargs['proxies']['http']
        assert proxy_url.startswith('http://')
    
    def test_proxy_persistence(self):
        """Test that proxy configurations persist across sessions."""
        # Add proxy
        xts_alias.add_proxy('persistent_proxy', 'proxy.example.com:8080',
                           username='user', password='pass')
        
        # Reload proxies (simulating new session)
        proxies = xts_alias.load_proxies()
        
        assert 'persistent_proxy' in proxies
        assert proxies['persistent_proxy']['proxy'] == 'proxy.example.com:8080'
        assert proxies['persistent_proxy']['username'] == 'user'
        
        # Cleanup
        xts_alias.remove_proxy('persistent_proxy')
    
    def test_update_proxy_configuration(self):
        """Test updating existing proxy configuration."""
        # Add initial proxy
        xts_alias.add_proxy('update_test', 'old.proxy.com:8080')
        
        # Update with new configuration
        xts_alias.add_proxy('update_test', 'new.proxy.com:3128',
                           username='newuser', password='newpass')
        
        proxies = xts_alias.load_proxies()
        assert proxies['update_test']['proxy'] == 'new.proxy.com:3128'
        assert proxies['update_test']['username'] == 'newuser'
        
        # Cleanup
        xts_alias.remove_proxy('update_test')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

