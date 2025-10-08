import pytest
import yaml
import os
import sys
import pathlib

from io import StringIO

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(dir_path+'/../')

from xts_core.plugins.xts_allocator_client import XTSAllocatorClient
from xts_core.plugins.base_plugin import plugin_utils

@pytest.fixture
def tmp_path():
    workspace = pathlib.Path.cwd().joinpath('xts_test_workspace')
    os.makedirs(workspace, exist_ok=True)
    return workspace

class StdOutCapture(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self
    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio    # free up some memory
        sys.stdout = self._stdout

def test_provided_args():
    '''Test provided_args property.'''
    expected_args = [
        ('allocate', 'Request allocation of a slot.'),
        ('alloc', 'Alias for allocate.'),
        ('allocator', 'Make changes to the allocator server.'),
        ('deallocate', 'Free an allocated slot.'),
        ('dealloc', 'Alias of deallocate'),
        ('free', 'Alias of deallocate'),
    ]
    assert XTSAllocatorClient().provided_args == expected_args

def test_provided_positionals():
    '''Test provided_positionals property.'''
    expected_positionals = ['allocate', 'alloc', 'allocator', 'deallocate', 'dealloc', 'free']
    assert XTSAllocatorClient().provided_positionals == expected_positionals


def test_load_servers(tmp_path:pathlib.Path, monkeypatch:pytest.MonkeyPatch):
    '''Test loading server configurations from a YAML file.'''
    mock_yaml_data = {'server1': 'config1', 'server2': 'config2'}
    config_file = tmp_path / 'test_xts_servers.yaml'
    with open(config_file, 'w') as f:
        yaml.safe_dump(mock_yaml_data, f)
    monkeypatch.setattr(XTSAllocatorClient, 'CONFIG_FILE', str(config_file))
    servers = XTSAllocatorClient.load_servers()
    assert servers == mock_yaml_data

def test_save_servers(tmp_path:pathlib.Path, monkeypatch:pytest.MonkeyPatch):
    '''Test saving server configurations to a YAML file.'''
    config_file = tmp_path / 'test_xts_servers.yaml'
    monkeypatch.setattr(XTSAllocatorClient, 'CONFIG_FILE', str(config_file))
    data_to_save = {'server3': 'config3'}
    XTSAllocatorClient.save_servers(data_to_save)
    with open(config_file, 'r') as f:
        saved_data = yaml.safe_load(f)
    assert saved_data == data_to_save

def test_allocator_list(monkeypatch:pytest.MonkeyPatch):
    def mock_load_servers(obj: XTSAllocatorClient):
        return {'Test': {'url':'https://localhost:5000'}}
    monkeypatch.setattr(XTSAllocatorClient,'load_servers', mock_load_servers)
    args = ['allocator', 'list']
    with StdOutCapture() as output:
        XTSAllocatorClient().run(args)
    output_str = '\n'.join(output)
    assert 'Test: https://localhost:5000' in output_str

def test_allocator_add(tmp_path:pathlib.Path, monkeypatch:pytest.MonkeyPatch):
    config_file = tmp_path / 'test_xts_servers.yaml'
    monkeypatch.setattr(XTSAllocatorClient, 'CONFIG_FILE', str(config_file))
    with open(config_file, 'w+') as f:
        f.write('')
    args = ['allocator', 'add', 'Test', 'https://localhost']
    client = XTSAllocatorClient()
    client.run(args)
    with open(client.CONFIG_FILE, 'r') as xts_config:
        loaded_yaml = yaml.load(xts_config, yaml.SafeLoader)
    assert {'Test': {'url': 'https://localhost'}} == loaded_yaml

def test_allocator_remove(tmp_path:pathlib.Path, monkeypatch:pytest.MonkeyPatch):
    aliases = ['remove', 'rm']
    config_file = tmp_path / 'test_xts_servers.yaml'
    monkeypatch.setattr(XTSAllocatorClient, 'CONFIG_FILE', str(config_file))
    for alias in aliases:
        with open(config_file, 'w') as cfg:
            yaml.dump({'Test':{'url':'https://localhost'}}, cfg)
        args = ['allocator', alias, 'Test']
        with StdOutCapture() as output:
            XTSAllocatorClient().run(args)
        with open(config_file, 'r', encoding='utf-8') as cfg:
            cfg_content = cfg.read()
        assert cfg_content == ''

def test_allocator_search(monkeypatch:pytest.MonkeyPatch):
    def mock_send_request(obj:XTSAllocatorClient, method, url, data=None):
        assert method == 'POST'
        assert 'https://localhost:5000/list_slots' == url
        assert {'platform': 'Linux'} == data
        return {'slots': [
            {'rackName': 'rack1',
             'slotName': 'slot1',
             'platform': 'Linux',
             'description': 'Test slot 1',
             'tags': ['Test','Mock']}
             ]}
    monkeypatch.setattr(XTSAllocatorClient, '_send_request', mock_send_request)
    args = ['allocator',
            'search',
            '--server',
            'https://localhost:5000',
            '--platform',
            'Linux']
    with StdOutCapture() as output:
        XTSAllocatorClient().run(args)
    output_str = '\n'.join(output)
    assert 'Matching slots on server [https://localhost:5000]' in output_str
    assert 'Rackname' in output_str
    assert 'rack1' in output_str
    assert 'Slotname' in output_str
    assert 'slot1' in output_str
    assert 'Platform' in output_str
    assert 'Linux' in output_str
    assert 'Description' in output_str
    assert 'Test slot 1' in output_str
    assert 'Tags' in output_str
    assert 'Test, Mock' in output_str

def test_allocator_list_slots(monkeypatch:pytest.MonkeyPatch):
    def mock_send_request(obj:XTSAllocatorClient, method, url, data=None):
        assert method == 'GET'
        assert 'https://localhost:5000/list_slots' == url
        return {'slots': [
            {'rackName': 'rack1',
             'slotName': 'slot1',
             'platform': 'Linux',
             'description': 'Test slot 1',
             'tags': ['Test','Mock']}
             ]}
    monkeypatch.setattr(XTSAllocatorClient, '_send_request', mock_send_request)
    args = ['allocator',
            'list-slots',
            '--server',
            'https://localhost:5000']
    with StdOutCapture() as output:
        XTSAllocatorClient().run(args)
    output_str = '\n'.join(output)
    assert 'Slots on allocator server [https://localhost:5000]' in output_str
    assert 'Rackname' in output_str
    assert 'rack1' in output_str
    assert 'Slotname' in output_str
    assert 'slot1' in output_str
    assert 'Platform' in output_str
    assert 'Linux' in output_str
    assert 'Description' in output_str
    assert 'Test slot 1' in output_str
    assert 'Tags' in output_str
    assert 'Test, Mock' in output_str

def test_allocator_add_slot(monkeypatch:pytest.MonkeyPatch):
    def mock_send_request(obj:XTSAllocatorClient, method, url, data=None):
        assert method == 'POST'
        assert url == 'https://localhost:5000/add_slot'
        assert data == {'rackName':'rack1',
                        'slotName':'slot1',
                        'platform':'Linux',
                        'description': 'Test slot',
                        'tags': ['test', 'mock'],
                        'state': 'free',
                        'owner_email':'test@testmail.com'}
        return {'message': 'Slot added successfully.'}
    monkeypatch.setattr(XTSAllocatorClient, '_send_request', mock_send_request)
    args = ['allocator',
            'add-slot',
            '--server',
            'https://localhost:5000',
            '--rack-name',
            'rack1',
            '--slot-name',
            'slot1',
            '--platform',
            'Linux',
            '--description',
            'Test slot',
            '--tags',
            'test',
            'mock',
            '--state',
            'free',
            '--owner-email',
            'test@testmail.com']
    with StdOutCapture() as output:
        XTSAllocatorClient().run(args)
    assert 'Slot added successfully' in '\n'.join(output)

def test_allocator_update_slot(monkeypatch:pytest.MonkeyPatch):
    def mock_send_request(obj:XTSAllocatorClient, method, url, data=None):
        assert method == 'POST'
        assert url == 'https://localhost:5000/update_slot'
        assert data == {'slot_id' : 1,
                        'rackName': 'rack1',
                        'platform' : 'Linux'}
        return {'message': 'Slot updated successfully.'}
    monkeypatch.setattr(XTSAllocatorClient, '_send_request', mock_send_request)
    args = ['allocator',
            'update-slot',
            '--server',
            'https://localhost:5000',
            '--slot-id',
            '1',
            '--rack-name',
            'rack1',
            '--platform',
            'Linux']
    with StdOutCapture() as output:
        XTSAllocatorClient().run(args)
    assert 'Slot updated successfully' in '\n'.join(output)

def test_allocator_remove_slot(monkeypatch:pytest.MonkeyPatch):
    def mock_send_request(obj:XTSAllocatorClient, method, url, data=None):
        assert method == 'POST'
        assert url == 'https://localhost:5000/delete_slot'
        assert data == {'slot_id' : 1}
        return {'message': 'Slot deleted successfully.'}
    monkeypatch.setattr(XTSAllocatorClient, '_send_request', mock_send_request)
    aliases = ['remove-slot', 'rm-slot']
    for alias in aliases:
        args = ['allocator', alias, '--server', 'https://localhost:5000', '--slot-id', '1']
        with StdOutCapture() as output:
            XTSAllocatorClient().run(args)
        assert 'Slot deleted successfully.' in '\n'.join(output)

def test_allocate_slot(monkeypatch:pytest.MonkeyPatch):
    '''Test the allocation of a slot.'''
    mock_response = {'slot_id': '12345'}
    def mock_send_request(client:XTSAllocatorClient, method, url, data=None):
        return mock_response if method == 'POST' else None
    monkeypatch.setattr(XTSAllocatorClient, '_send_request', mock_send_request)
    args = ['allocate', '--server', 'http://example.com', '--platform', 'Linux']
    try:
        with StdOutCapture() as output:
            XTSAllocatorClient().run(args)
        assert mock_response.get('slot_id') in output
    except SystemExit:
        print('\n'.join(output))
        raise

def test_deallocate_slot(monkeypatch:pytest.MonkeyPatch):
    '''Test the deallocation of a slot.'''
    mock_response = {'status': 'deallocated'}
    def mock_send_request(obj, method, url, data=None):
        return mock_response if method == 'DELETE' else None
    monkeypatch.setattr(XTSAllocatorClient, '_send_request', mock_send_request)
    aliases = ['deallocate','free','dealloc']
    for alias in aliases:
        args = [alias, '--server', 'http://example.com', '--slot-id', '12345']
        try:
            with StdOutCapture() as out:
                XTSAllocatorClient().run(args)
            assert str(mock_response) in '\n'.join(out)
        except SystemExit:
            print(out)
            raise


if __name__ == '__main__':
    pytest.main([pathlib.Path(__file__),'-v'])