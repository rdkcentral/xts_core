import pytest
import requests
import yaml
import os
import sys

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(dir_path+"/../")

from src.yaml_runner import add_choices_to_help
from src.plugins.xts_allocator_client import XTSAllocatorClient

@pytest.fixture
def client():
    """Fixture to create an instance of XTSAllocatorClient."""
    return XTSAllocatorClient()

def test_provided_args(client):
    """Test provided_args property."""
    expected_args = [
        ('allocate', 'Request allocation of a slot.'),
        ('alloc', 'Alias for allocate.'),
        ('allocator', 'Make changes to the allocator server.'),
        ('deallocate', 'Free an allocated slot.'),
        ('dealloc', 'Alias of deallocate'),
        ('free', 'Alias of deallocate'),
    ]
    assert client.provided_args == expected_args


def test_provided_positionals(client):
    """Test provided_positionals property."""
    expected_positionals = ['allocate', 'alloc', 'allocator', 'deallocate', 'dealloc', 'free']
    assert client.provided_positionals == expected_positionals


def test_load_servers(monkeypatch, tmp_path):
    """Test loading server configurations from a YAML file."""
    mock_yaml_data = {"server1": "config1", "server2": "config2"}
    config_file = tmp_path / "test_xts_servers.yaml"

    with open(config_file, "w") as f:
        yaml.safe_dump(mock_yaml_data, f)

    monkeypatch.setattr(XTSAllocatorClient, "CONFIG_FILE", str(config_file))
    
    servers = XTSAllocatorClient.load_servers()
    assert servers == mock_yaml_data


def test_save_servers(monkeypatch, tmp_path):
    """Test saving server configurations to a YAML file."""
    config_file = tmp_path / "test_xts_servers.yaml"
    monkeypatch.setattr(XTSAllocatorClient, "CONFIG_FILE", str(config_file))
    
    data_to_save = {"server3": "config3"}
    XTSAllocatorClient.save_servers(data_to_save)

    with open(config_file, "r") as f:
        saved_data = yaml.safe_load(f)

    assert saved_data == data_to_save


def test_allocate_slot(monkeypatch, client):
    """Test the allocation of a slot."""
    mock_response = {"slot_id": "12345"}
    
    def mock_send_request(method, url, data=None):
        return mock_response if method == "POST" else None

    monkeypatch.setattr(XTSAllocatorClient, "send_request", mock_send_request)

    args = ["--server", "http://example.com", "--platform", "Linux"]
    result = client._allocate_slot(args)
    assert result == mock_response


def test_deallocate_slot(monkeypatch, client):
    """Test the deallocation of a slot."""
    mock_response = {"status": "deallocated"}

    def mock_send_request(method, url, data=None):
        return mock_response if method == "POST" else None

    monkeypatch.setattr(XTSAllocatorClient, "send_request", mock_send_request)

    args = ["--server", "http://example.com", "--slot", "12345"]
    result = client._deallocate_slot(args)
    assert result == mock_response
