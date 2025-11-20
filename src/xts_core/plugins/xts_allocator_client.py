#!/usr/bin/env python3

import argparse
import os
import requests
import sys

import yaml
import rich
from rich.table import Table
try:
    from base_plugin import BaseXTSPlugin, plugin_utils, XTSArgumentParser
except:
    from xts_core.plugins.base_plugin import BaseXTSPlugin, plugin_utils, XTSArgumentParser



class XTSAllocatorClient(BaseXTSPlugin):
    '''
    Command-line interface client for interacting with an allocator server that manages test slots.

    It provides commands for:
        - Allocating and deallocating test slots
        - Managing allocator server configurations
        - Searching and listing available test slots
    '''
    CONFIG_FILE = BaseXTSPlugin.config_dir.joinpath('.xts_servers.yaml')

    _positional_args = [
        ('allocate', 'Request allocation of a slot.'),
        ('alloc', 'Alias for allocate.'),
        ('allocator', 'Make changes to the allocator server.'),
        ('deallocate', 'Free an allocated slot.'),
        ('dealloc', 'Alias of deallocate'),
        ('free', 'Alias of deallocate'),
    ]

    def __init__(self):
        '''
        Initialise the CLI parser and set up command arguments.
        '''
        super().__init__()

    @property
    def provided_args(cls):
        '''Return a list of available CLI commands and their descriptions.'''
        return cls._positional_args

    @property
    def provided_positionals(cls):
        '''Return a list of available command names (without descriptions).'''
        return list(map(lambda x: x[0] if isinstance(x,tuple) else x, cls.provided_args))

    @staticmethod
    def _send_request(method, url, data=None) -> dict:
        '''
        Send an HTTP request to the allocator server.

        Args:
            method (str): The HTTP method (e.g. 'GET', 'POST', 'DELETE').
            url (str): The request URL.
            data (dict, optional): JSON payload to send.

        Returns:
            dict: The JSON response from the server if successful.
            None: If the request fails.
        '''
        if not url.startswith(('http://', 'https://')):
            url = f'http://{url}'
        plugin_utils.debug(f'Sending request to: {url}')
            
        try:
            response = requests.request(method, url, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            plugin_utils.error(f'Error during request: {e}')


    @staticmethod
    def _format_slots_list_to_table(response:list[dict]) -> Table:
        '''Format the list of slot dictionaries into a rich table
        that can display their fields.

        Args:
            response (list[dict]): list of dictionaries containing information about slots.

        Returns:
            Table: Rich table object that can be used to print the slot information in a table.
        '''
        table_headers = map(lambda x: x.capitalize(),response[0].keys())
        resp_table = Table(*table_headers)
        
        for entry in response:
            row_values = []
            for value in entry.values():
                if isinstance(value, list):
                    row_values.append(', '.join(map(str, value)))
                elif isinstance(value, dict):
                    row_values.append(str(value))
                else:
                    row_values.append(str(value) if value is not None else "")
            resp_table.add_row(*row_values)
        return resp_table

    @staticmethod
    def load_servers():
        '''
        Load allocator server configurations from a YAML file.

        Returns:
            dict: A dictionary of saved allocator servers.
        '''
        if os.path.exists(XTSAllocatorClient.CONFIG_FILE):
            with open(XTSAllocatorClient.CONFIG_FILE, 'r') as file:
                return yaml.safe_load(file) or {}
        return {}

    @staticmethod
    def save_servers(servers):
        '''
        Save allocator server configurations to a YAML file.

        Args:
            servers (dict): Dictionary of servers to save.
        '''
        with open(XTSAllocatorClient.CONFIG_FILE, 'w') as file:
            if bool(servers):
                yaml.safe_dump(servers, file)
            else:
                file.write('')

    def _setup_allocate_args(self):
        '''Setup the subparser for the allocate command.
        '''
        allocate_parser = self._subparsers.add_parser('allocate', aliases=['alloc'])
        allocate_parser.add_argument('--slot-id', 
                                     dest='id', 
                                     help='Slot ID to allocate. If provided, --platform and --tags are ignored.')
        allocate_parser.add_argument('--platform', 
                                     dest='platform', 
                                     help='Platform required for allocation. Required if --tags is used.')
        allocate_parser.add_argument('--tags', 
                                     dest='tags', 
                                     nargs='+', 
                                     help='Search tags. Requires --platform.')
        allocate_parser.add_argument('--server', 
                                     dest='server', 
                                     required=True, 
                                     help='Allocator server address.')
        allocate_parser.add_argument(
                                    '--user-email',
                                    dest='user_email',
                                    required=False,
                                    help='Email of the user performing the allocation')

    def _setup_allocator_args(self):
        '''Setup the subparsers for the allocator command.
        '''
        allocator_parser = self._subparsers.add_parser('allocator')
        allocator_subparsers = allocator_parser.add_subparsers(dest='allocator_subcommand', required=True, metavar='COMMAND')

        # remove
        # Since a lot of these parsers share arguments we can use the base parsers as parents
        # to save on adding the same arguments multiple times.
        remove_base = XTSArgumentParser('remove base', add_help=False,)
        remove_base.add_argument('name', help='Name of the server to remove')
        remove_parser = allocator_subparsers.add_parser('remove',
                                                        help='Remove an allocator server',
                                                        parents=[remove_base],
                                                        aliases=['rm'])
        # add
        add_parser = allocator_subparsers.add_parser('add',
                                                     help='Add an allocator server',
                                                     parents=[remove_base])
        add_parser.add_argument('url', help='URL for the allocator server')
        # list
        allocator_subparsers.add_parser('list', help='List all known allocators')
        base_parser = XTSArgumentParser('base', add_help=False)
        base_parser.add_argument('--server', required=True, help='Server URL')
        # search
        search_base = XTSArgumentParser('search_base',
                                              add_help=False,
                                              parents=[base_parser])
        search_base.add_argument('--platform', help='Platform of DUT')
        search_base.add_argument('--description', help='Description of slot')
        search_base.add_argument('--tags', nargs='+', help='Tags of slot')
        search_parser = allocator_subparsers.add_parser('search',
                                                        help='Search for slots on an allocator server',
                                                        parents=[search_base])
        # add-slot
        add_base = XTSArgumentParser('add_base',
                                            add_help=False,
                                            parents=[search_base])
        add_base.add_argument('--owner-email', help='Owner email (if allocated).', dest='owner_email')
        add_slot_parser = allocator_subparsers.add_parser('add-slot',
                                                          help='Add a slot to the allocator server',
                                                          parents=[add_base])
        add_slot_parser.add_argument('--rack-name', required=True, help='Rack name of the slot.', dest='rack_name')
        add_slot_parser.add_argument('--slot-name', required=True, help='Slot name.', dest='slot_name')
        add_slot_parser.add_argument('--state', choices=['free', 'allocated'], default='free', help='State of the slot.')

        # update-slot
        update_slot_parser= allocator_subparsers.add_parser('update-slot',
                                                            help='Update an existing slot on the allocator server',
                                                            parents=[add_base])
        update_slot_parser.add_argument('--slot-id', required=True, type=int, help='ID of the slot to update.')
        update_slot_parser.add_argument('--rack-name', required=True, help='Rack name of the slot.', dest='rack_name')
        update_slot_parser.add_argument('--slot-name', help='Slot name.', dest='slot_name')
        update_slot_parser.add_argument('--state', choices=['free', 'allocated'], help='State of the slot.')

        # remove-slot
        remove_slot_parser = allocator_subparsers.add_parser('remove-slot',
                                                             aliases=['rm-slot'],
                                                             help='Remove a slot from the allocator server',
                                                             parents=[base_parser])
        remove_slot_parser.add_argument('--slot-id', required=True, type=int, help='ID of the slot to remove.', dest='slot_id')
        # list-slots
        list_parser = allocator_subparsers.add_parser('list-slots', 
                                                      help='List slot information from an allocator server',
                                                      parents=[base_parser])

    def _setup_deallocate_args(self):
        '''Setup the subparser for the deallocate command.
        '''
        deallocate_parser = self._subparsers.add_parser('deallocate', aliases=['dealloc', 'free'])
        deallocate_parser.add_argument('--slot-id',
                                       dest='slot_id',
                                       action='store',
                                       default=None,
                                       help='ID number of slot to free',
                                       nargs=1,
                                       type=int,
                                       required=True)
        deallocate_parser.add_argument('--server', 
                                       dest='server', 
                                       required=True, 
                                       help='Allocator server address.')
    
    def _setup_args(self):
        '''Setup all the subparsers for the allocator client.
        '''
        self._setup_allocate_args()
        self._setup_allocator_args()
        self._setup_deallocate_args()

    def run(self, args: list[str]):
        '''
        Parse and execute the provided CLI command.

        Args:
            args (list): Command-line arguments.
        '''
        self._setup_args()
        parsed_args = self._prog_parser.parse_args(args)
        parsed_args_dict = vars(parsed_args)
        match parsed_args_dict.pop('command'):
            case 'allocate'| 'alloc':
                self._allocate_slot(**parsed_args_dict)
            case 'allocator':
                self._allocator(**parsed_args_dict)
            case 'deallocate' | 'dealloc' | 'free':
                self._deallocate_slot(**parsed_args_dict)
            case _:
                self._prog_parser.print_help()
                raise SystemExit(1)

    def _allocate_slot(self,
                       server: str,
                       id: int = None,
                       platform: str = None,
                       tags: list = None,
                       user_email: str = None):
        '''
        Allocate a test slot and retrieve its rack configuration.

        Args:
            args (dict): dict of parser arguments for slot allocation.

        Returns:
            dict: Rack configuration of the allocated slot, if successful.
        '''
        if tags and not platform:
            plugin_utils.error('[default]--tags[/default] can only be used if [default]--platform[/default] is specified.')
        slot_payload = {}
        if id:
            #ignore --platform and --tags
            slot_payload['id'] = id
            plugin_utils.warning('Ignoring [default]--platform[/default] and [default]--tags[/default] because [default]--id[/default] was provided.')
        else:
            #use --platform (required for allocation)
            if not platform:
                plugin_utils.error('[default]--platform[/default] is required when [default]--id[/default] is not provided.')
            slot_payload['platform'] = platform
            
            if tags:
                slot_payload['tags'] = tags

        user_email = user_email or os.getenv("USER_EMAIL", "default@xts.local")

        payload = {
            "user": {"email": user_email},
            "slot": slot_payload
        }

        response = self._send_request('POST', f'{server}/allocate_slot', payload)
        
        if response and 'slot_id' in response:
            allocated_slot_id = response['slot_id']
            plugin_utils.info(f'Slot allocated successfully: {allocated_slot_id}')
            
            # Fetch the rack configuration for the allocated slot
            rack_config = self._get_rack_config(server, allocated_slot_id)
            
            if rack_config:
                plugin_utils.debug(f'Rack Configuration: {rack_config}')
                return rack_config
            else:
                plugin_utils.error('Failed to retrieve rack configuration.')
        else:
            plugin_utils.error('[red]Slot allocation failed.[/red]')

    def _get_rack_config(self, server: str, slot_id: str) -> dict:
        '''
        Retrieves the rack configuration for a given slot ID.

        Args:
            server (str): The allocator server address.
            slot_id (str): The ID of the allocated slot.

        Returns:
            dict: Rack configuration details if successful, else None.
        '''
        response = self._send_request('GET', f'{server}/slot/{slot_id}/rack-config')
        return response

        
    def _allocator(self, **kwargs):
        '''
        Manage allocator server (list, add, remove).

        Args:
            args (list): Command-line arguments.
        '''
        servers = self.load_servers()
        match kwargs.pop('allocator_subcommand'):
            case 'add':
                name = kwargs.get('name')
                url = kwargs.get('url')
                if name not in servers:
                    servers[name] = {'url': url}
                    self.save_servers(servers)
                    plugin_utils.info(f'Server added: {name} -> {url}')
                else:
                    plugin_utils.warning(f'Server already exists: {name}')

            case 'remove' | 'rm':
                name = kwargs.get('name')
                if name in servers:
                    del servers[name]
                    self.save_servers(servers)
                    plugin_utils.info(f'Server removed: {name}')
                else:
                    plugin_utils.error(f'Server not found: {name}')

            case 'list':
                if servers:
                    plugin_utils.info('Configured servers:')
                    for name, info in servers.items():
                        plugin_utils.info(f' - {name}: {info.get("url", "N/A")}')
                else:
                    plugin_utils.error('No servers configured.')

            case 'search':
                server = kwargs.get('server')
                search_filters = {}
                if platform:= kwargs.get('platform'):
                    search_filters['platform'] = platform
                if description:= kwargs.get('description'):
                    search_filters['description'] = description
                if tags:= kwargs.get('tags'):
                    search_filters['tags'] = tags
                response = self._list_slots(server, filters=search_filters)

                slots = response.get('slots')
                if slots:
                    plugin_utils.info(f'Matching slots on server \[{server}]:')
                    table = self._format_slots_list_to_table(slots)
                    rich.print(table)
                else:
                    plugin_utils.error(f'No matching slots found on server \[{server}].')

            case 'add-slot':
                server = kwargs.pop('server')
                rack_name = kwargs.pop('rack_name')
                slot_name = kwargs.pop('slot_name')
                platform = kwargs.pop('platform')
                self._add_slot(server,
                               rack_name,
                               slot_name,
                               platform,
                               **kwargs)

            case 'update-slot':
                server = kwargs.pop('server')
                slot_id = kwargs.pop('slot_id')
                rack_name = kwargs.pop('rack_name')
                self._update_slot(server,
                                  slot_id,
                                  rack_name,
                                  **kwargs)

            case 'remove-slot' | 'rm-slot':
                self._remove_slot(kwargs.get('slot_id'), kwargs.get('server'))

            case 'list-slots':
                server = kwargs.get('server')
                resp = self._list_slots(server)
                if len(slots:= resp.get('slots',[])) >= 1:
                    plugin_utils.info(f'Slots on allocator server \[{server}]:')
                    table = self._format_slots_list_to_table(resp.get('slots'))
                    rich.print(table)
                else:
                    plugin_utils.warning(f'The server \[{server}] has no slots configured.')
            case _:
                plugin_utils.error('The allocator subcommand is not implemented')


    def _deallocate_slot(self, slot_id: int, server: str):
        '''
        Deallocate a previously allocated slot.

        Args:
            args (list): Command-line arguments.
        '''
        payload = {'id': slot_id}
        response = self._send_request('DELETE', f'{server}/deallocate', payload)
        if response:
            plugin_utils.info(f'Slot deallocated successfully: {response}')
        else:
            plugin_utils.error(f'Could not deallocate slot \[{slot_id}] from server \[{server}]')

    def _list_slots(self, server:str, filters: dict=None) -> dict:
        '''
        List all available slots from the allocator server.

        Args:
            args (list): Command-line arguments.
        '''
        request_type = 'GET'
        request_url = f'{server}/list_slots'
        if filters:
            request_type='POST'
        response = self._send_request(request_type, request_url, filters)
        return response
    
    def _add_slot(self,
                  server:str,
                  rack_name:str,
                  slot_name:str,
                  platform:str,
                  owner_email:str|None,
                  state:str='',
                  description:str='',
                  tags:list[str]=[]):
        '''
        Add a new slot to the allocator server.

        Args:
            args (list): Command-line arguments.
        '''
        payload = {
            'rackName': rack_name,
            'slotName': slot_name,
            'description': description,
            'tags': tags,
            'platform': platform,
            'state': state,
            'owner_email': owner_email,
        }
        response = self._send_request('POST', f'{server}/add_slot', payload)
        if response:
            plugin_utils.info(response.get('message'))

    def _update_slot(self,
                     server:str,
                     slot_id:int,
                     rack_name:str,
                     slot_name:str | None = None,
                     description:str | None = None,
                     tags: list | None = None,
                     platform: str | None = None,
                     state: str | None = None,
                     owner_email: str | None = None):
        '''
        Update an existing slot in the allocator server.

        Args:
            args (list): Command-line arguments.
        '''
        if not any([rack_name,
                    slot_name,
                    description,
                    tags,
                    platform,
                    state,
                    owner_email]):
            plugin_utils.error('At least one field must be provided for update.')
            sys.exit(1)
        # Required fields
        payload = {
            'slot_id': slot_id
        }
        if rack_name:
            payload['rackName'] = rack_name
        if slot_name:
            payload['slotName'] = slot_name
        if description:
            payload['description'] = description
        if tags:
            payload['tags'] = tags
        if platform:
            payload['platform'] = platform
        if state:
            payload['state'] = state
        if owner_email:
            payload['owner_email'] = owner_email
        response = self._send_request('POST', f'{server}/update_slot', payload)
        if response:
            plugin_utils.info(response.get('message'))

    def _remove_slot(self, slot_id: int, server: str):
        '''
        Remove a slot from the allocator server.

        Args:
            args (list): Command-line arguments.
        '''
        payload = {'slot_id': slot_id}
        response = self._send_request('POST', f'{server}/delete_slot', payload)
        if response:
            plugin_utils.info(response.get('message'))

if __name__ == '__main__':
    import sys
    XTSAllocatorClient().run(sys.argv[1:])
