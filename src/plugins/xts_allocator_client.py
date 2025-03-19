#!/usr/bin/env python3

import os
import sys
import requests
import yaml
import argparse
import rich

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(dir_path+"/../../")

from yaml_runner import add_choices_to_help

class XTSAllocatorClient():
    """
    Command-line interface client for interacting with an allocator server that manages test slots.

    It provides commands for:
        - Allocating and deallocating test slots
        - Managing allocator server configurations
        - Searching and listing available test slots
    """
    CONFIG_FILE = os.path.expanduser("~/.xts_servers.yaml")

    _positional_args = [
        ('allocate', 'Request allocation of a slot.'),
        ('alloc', 'Alias for allocate.'),
        ('allocator', 'Make changes to the allocator server.'),
        ('deallocate', 'Free an allocated slot.'),
        ('dealloc', 'Alias of deallocate'),
        ('free', 'Alias of deallocate'),
        ('search', 'Search available slots.'),
        ('list', 'List all slots.')
    ]

    def __init__(self):
        """
        Initialise the CLI parser and set up command arguments.
        """
        self._parser = argparse.ArgumentParser(add_help=False)
        self._subparsers =self._parser.add_subparsers()
        self._initial_parser = self._subparsers.add_parser('', add_help=False)
        self._initial_parser.add_argument('command',
                                          action='store',
                                          help='The command to run',
                                          choices=self.provided_positionals,
                                          default=[],
                                          metavar='COMMAND')

    @property
    def provided_args(cls):
        """Return a list of available CLI commands and their descriptions."""
        return cls._positional_args

    @property
    def provided_positionals(cls):
        """Return a list of available command names (without descriptions)."""
        return list(map(lambda x: x[0] if isinstance(x,tuple) else x, cls.provided_args))

    @staticmethod
    def send_request(method, url, data=None):
        """
        Send an HTTP request to the allocator server.

        Args:
            method (str): The HTTP method (e.g. 'GET', 'POST', 'DELETE').
            url (str): The request URL.
            data (dict, optional): JSON payload to send.

        Returns:
            dict: The JSON response from the server if successful.
            None: If the request fails.
        """
        try:
            response = requests.request(method, url, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            rich.print(f"[red]Error during request: {e}[/red]")
            raise SystemExit(1)

    @staticmethod
    def load_servers():
        """
        Load allocator server configurations from a YAML file.

        Returns:
            dict: A dictionary of saved allocator servers.
        """
        if os.path.exists(XTSAllocatorClient.CONFIG_FILE):
            with open(XTSAllocatorClient.CONFIG_FILE, 'r') as file:
                return yaml.safe_load(file) or {}
        return {}

    @staticmethod
    def save_servers(servers):
        """
        Save allocator server configurations to a YAML file.

        Args:
            servers (dict): Dictionary of servers to save.
        """
        with open(XTSAllocatorClient.CONFIG_FILE, 'w') as file:
            yaml.safe_dump(servers, file)

    def run(self, args: list):
        """
        Parse and execute the provided CLI command.

        Args:
            args (list): Command-line arguments.
        """
        parsed_args, remaining_args = self._initial_parser.parse_known_args(args)
        if parsed_args.command in ('allocate', 'alloc'):
            self._allocate_slot(remaining_args)
        elif parsed_args.command in ('allocator'):
            self._allocator(remaining_args)
        elif parsed_args.command in ('deallocate', 'dealloc', 'free'):
            self._deallocate_slot(remaining_args)
        elif parsed_args.command == 'search':
            self._search_slots(remaining_args)
        elif parsed_args.command == 'list':
            self._list_slots(remaining_args)
        else:
            print(self._initial_help)
        raise SystemExit(0)

    def run_flags(self, flags: list):
        pass

    def _allocate_slot(self, args: list):
        """
        Allocate a test slot and retrieve its rack configuration.

        Args:
            args (list): List of command-line arguments for slot allocation.

        Returns:
            dict: Rack configuration of the allocated slot, if successful.
        """
        allocate_parser = self._subparsers.add_parser('allocate')
        allocate_parser.add_argument('--id', 
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
        parsed_args = allocate_parser.parse_args(args)

        if parsed_args.tags and not parsed_args.platform:
            rich.print("[red]Error: --tags can only be used if --platform is specified.[/red]")
            sys.exit(1)

        if parsed_args.id:
            #ignore --platform and --tags
            payload = {"id": parsed_args.id}
            rich.print("[yellow]Ignoring --platform and --tags because --id was provided.[/yellow]")
        else:
            #use --platform (required for allocation)
            if not parsed_args.platform:
                rich.print("[red]Error: --platform is required when --id is not provided.[/red]")
                sys.exit(1)
            payload = {"platform": parsed_args.platform, "tags": parsed_args.tags}

        response = self.send_request("POST", f"{parsed_args.server}/allocate", payload)
        
        if response and "slot_id" in response:
            allocated_slot_id = response["slot_id"]
            rich.print(f"[green]Slot allocated successfully: {allocated_slot_id}[/green]")
            
            # Fetch the rack configuration for the allocated slot
            rack_config = self._get_rack_config(parsed_args.server, allocated_slot_id)
            
            if rack_config:
                rich.print(f"[cyan]Rack Configuration: {rack_config}[/cyan]")
                return rack_config
            else:
                rich.print("[red]Failed to retrieve rack configuration.[/red]")
                return None
        else:
            rich.print("[red]Slot allocation failed.[/red]")
            return None

    def _get_rack_config(self, server: str, slot_id: str) -> dict:
        """
        Retrieves the rack configuration for a given slot ID.

        Args:
            server (str): The allocator server address.
            slot_id (str): The ID of the allocated slot.

        Returns:
            dict: Rack configuration details if successful, else None.
        """
        response = self.send_request("GET", f"{server}/slot/{slot_id}/rack-config")
        
        if response:
            return response
        else:
            rich.print(f"[red]Failed to retrieve rack configuration for slot {slot_id}.[/red]")
            return None
        
    def _allocator(self, args: list):
        """
        Manage allocator server (list, add, remove).

        Args:
            args (list): Command-line arguments.
        """
        allocator_parser = self._subparsers.add_parser('allocator', add_help=False)
        allocator_choices = [('list', 'List all known allocators'),
                             ('add', 'Add an allocator server'),
                             ('remove', 'Remove an allocator server')]
        
        # extract only the command names for argparse choices
        allocator_commands = [cmd[0] for cmd in allocator_choices]

        # manually add help argument since add_help=False
        allocator_parser.add_argument("-h", "--help", 
                                      action="help", 
                                      help="Show the help information")
        
        allocator_parser.add_argument('command',
                                      choices=allocator_commands,  # Only command names
                                      help='The command to run',
                                      metavar='COMMAND')
        
        allocator_parser.add_argument('--server', 
                                      help='Server URL for add/remove commands.')
        
        if not args:
            allocator_parser.print_help()
            raise SystemExit(0)


        parsed_args = allocator_parser.parse_args(args)
        servers = self.load_servers()
        
        
        if parsed_args.command == 'add':
            if parsed_args.server not in servers:
                servers[parsed_args.server] = {}
                self.save_servers(servers)
                rich.print(f"[green]Server added: {parsed_args.server}[/green]")
            else:
                rich.print(f"[yellow]Server already exists: {parsed_args.server}[/yellow]")

        elif parsed_args.command == 'remove':
            if parsed_args.server in servers:
                del servers[parsed_args.server]
                self.save_servers(servers)
                rich.print(f"[green]Server removed: {parsed_args.server}[/green]")
            else:
                rich.print(f"[red]Server not found: {parsed_args.server}[/red]")

        elif parsed_args.command == 'list':
            if servers:
                rich.print("[blue]Configured servers:[/blue]")
                for server in servers.keys():
                    rich.print(f" - {server}")
            else:
                rich.print("[yellow]No servers configured.[/yellow]")


    def _deallocate_slot(self, args: list):
        """
        Deallocate a previously allocated slot.

        Args:
            args (list): Command-line arguments.
        """
        deallocate_parser = self._subparsers.add_parser('deallocate')
        deallocate_parser.add_argument('--id',
                                       dest='id',
                                       action='store',
                                       default=None,
                                       help='ID number of slot to free',
                                       nargs=1,
                                       type=int)
        deallocate_parser.add_argument('--server', 
                                       dest='server', 
                                       required=True, 
                                       help='Allocator server address.')

        parsed_args = deallocate_parser.parse_args(args)
        
        # if parsed_args.id is None:
        #     rich.print('[red][bold]ID argument required.[/bold][/red]')
        #     deallocate_parser.print_help()
        #     raise SystemExit(1)
        # # TODO: Format args into json and post to /deallocate endpoint or requested server

        payload = {"id": parsed_args.id}
        response = self.send_request("DELETE", f"{parsed_args.server}/deallocate", payload)
        if response:
            rich.print(f"[green]Slot deallocated successfully: {response}[/green]")

    def _search_slots(self, args: list):
        """
        Search for available slots based on platform and tags.

        Args:
            args (list): Command-line arguments.
        """
        search_parser = self._subparsers.add_parser('search')
        search_parser.add_argument('--platform', 
                                   required=True, 
                                   help='Platform to search for.')
        search_parser.add_argument('--tags', 
                                   nargs='+', 
                                   help='Tags for filtering results.')
        search_parser.add_argument('--server', 
                                   required=True, 
                                   help='Allocator server address.')
        parsed_args = search_parser.parse_args(args)

        payload = {"platform": parsed_args.platform, "tags": parsed_args.tags}
        response = self.send_request("GET", f"{parsed_args.server}/search", payload)
        if response:
            rich.print(f"[green]Search results: {response}[/green]")

    def _list_slots(self, args: list):
        """
        List all available slots from the allocator server.

        Args:
            args (list): Command-line arguments.
        """
        list_parser = self._subparsers.add_parser('list')
        list_parser.add_argument('--server', 
                                 required=True, 
                                 help='Allocator server address.')
        parsed_args = list_parser.parse_args(args)

        response = self.send_request("GET", f"{parsed_args.server}/list")
        if response:
            rich.print(f"[green]Available slots: {response}[/green]")

if __name__ == '__main__':
    import sys
    XTSAllocatorClient().run(sys.argv[1:])
