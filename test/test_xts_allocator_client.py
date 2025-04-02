import os
import sys
import pytest
import requests
from unittest.mock import patch
from io import StringIO

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(dir_path+"/../")

from src.plugins.xts_allocator_client import XTSAllocatorClient

# Helper function to mock the send_request method
def mock_send_request(method, url, data=None):
    if method == "POST" and "/allocate" in url:
        if "invalid-server" in url:  # Simulate failure for invalid server
            return {"error": "Error during request"}
        if data.get("id"):
            return {"slot_id": "12345"}  # Simulate successful allocation
        elif data.get("platform") and data.get("tags"):
            return {"slot_id": "67890"}  # Simulate successful allocation
        return {"error": "Bad request"}  # Simulate failure
    if method == "GET" and "/slot/" in url:
        return {"rackName": "R1", "slotName": "S1"}  # Simulate successful rack config retrieval
    if method == "DELETE" and "/deallocate" in url:
        return {"message": "Slot deallocated"}  # Simulate successful deallocation
    return {"error": "Unknown request"}

@pytest.fixture
def mock_client():
    with patch.object(XTSAllocatorClient, 'send_request', side_effect=mock_send_request):
        yield XTSAllocatorClient()

def test_allocate_slot(mock_client):
    # Test allocation with ID
    args = ['allocate', '--id', '123', '--server', 'http://allocator-server']
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        with pytest.raises(SystemExit):  # to chatch SystemExit
            mock_client.run(args)
        output = mock_stdout.getvalue()
        assert "Slot allocated successfully: 12345" in output    

    # Test allocation with platform and tags
    args = ['allocate', '--platform', 'linux', '--tags', 'gpu', '--server', 'http://allocator-server']
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        with pytest.raises(SystemExit):
            mock_client.run(args)
        output = mock_stdout.getvalue()
        assert "Slot allocated successfully: 67890" in output

def test_deallocate_slot(mock_client):
    # Test deallocation with ID
    args = ['deallocate', '--id', '123', '--server', 'http://allocator-server']
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        with pytest.raises(SystemExit):
            mock_client.run(args)
        output = mock_stdout.getvalue()
        assert "Slot deallocated successfully" in output

def test_invalid_allocate_missing_platform(mock_client):
    # Test allocation failure due to missing platform when tags are used
    args = ['allocate', '--tags', 'gpu', '--server', 'http://allocator-server']
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        with pytest.raises(SystemExit):    
            mock_client.run(args)
        output = mock_stdout.getvalue()
        assert "Error: --tags can only be used if --platform is specified." in output

def test_allocator_add_server(mock_client):
    # Test adding an allocator server
    args = ['allocator', 'add', '--server', 'http://allocator-server']
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        with pytest.raises(SystemExit):
            mock_client.run(args)
        output = mock_stdout.getvalue()
        assert "Server added: http://allocator-server" in output

def test_allocator_remove_server(mock_client):
    # Test removing an allocator server
    args = ['allocator', 'remove', '--server', 'http://allocator-server']
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        with pytest.raises(SystemExit):
            mock_client.run(args)
        output = mock_stdout.getvalue()
        assert "Server removed: http://allocator-server" in output

def test_allocator_list_servers(mock_client):
    # Test listing allocator servers (empty configuration)
    args = ['allocator', 'list']
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        with pytest.raises(SystemExit):
            mock_client.run(args)
        output = mock_stdout.getvalue()
        assert "No servers configured." in output

def test_allocate_with_invalid_server(mock_client):
    # Test allocate with invalid server URL
    args = ['allocate', '--id', '123', '--server', 'http://invalid-server']
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        with pytest.raises(SystemExit):
            mock_client.run(args)
        output = mock_stdout.getvalue()
        assert "Error during request" in output

def test_missing_required_arguments(mock_client):
    # Test allocate with missing arguments
    args = ['allocate', '--server', 'http://allocator-server']
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        with pytest.raises(SystemExit):    
            mock_client.run(args)
        output = mock_stdout.getvalue()
        assert "Error: --platform is required when --id is not provided." in output

def test_search_slots(mock_client):
    # Test searching for slots
    args = ['allocator', 'search', '--server', 'http://allocator-server', '--platform', 'linux', '--tags', 'gpu']
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        with pytest.raises(SystemExit):    
            mock_client.run(args)
        output = mock_stdout.getvalue()
        assert "Matching slots:" in output
