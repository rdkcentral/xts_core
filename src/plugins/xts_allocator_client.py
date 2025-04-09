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
        allocator_parser.add_argument("-h", "--help", action="help", help="Show help information")

        allocator_subparsers = allocator_parser.add_subparsers(dest='command', required=True, metavar='COMMAND')

        # add
        add_parser = allocator_subparsers.add_parser('add', help='Add an allocator server')
        add_parser.add_argument('name', help='Name for the allocator server')
        add_parser.add_argument('url', help='URL for the allocator server')

        # remove
        remove_parser = allocator_subparsers.add_parser('remove', help='Remove an allocator server')
        remove_parser.add_argument('name', help='Name of the server to remove')

        # list
        allocator_subparsers.add_parser('list', help='List all known allocators')

        # search
        search_parser = allocator_subparsers.add_parser('search', help='Search for slots on an allocator server')
        search_parser.add_argument('--server', required=True, help='Server URL')
        search_parser.add_argument('--platform', help='Filter by platform')
        search_parser.add_argument('--description', help='Filter by description')
        search_parser.add_argument('--tags', nargs='+', help='Filter by tags')

        # add-slot, update-slot, remove-slot
        allocator_subparsers.add_parser('add-slot', help='Add a slot to the allocator server')
        allocator_subparsers.add_parser('update-slot', help='Update an existing slot on the allocator server')
        allocator_subparsers.add_parser('remove-slot', help='Remove a slot from the allocator server')
        
        # allocator_parser = self._subparsers.add_parser('allocator', add_help=False)
        # allocator_choices = [('search', 'Search for slots on an allocator server'),
        #                      ('list', 'List all known allocators'),
        #                      ('add', 'Add an allocator server'),
        #                      ('remove', 'Remove an allocator server'),
        #                      ('add-slot', 'Add a slot to the allocator server'),
        #                      ('update-slot', 'Update an existing slot on the allocator server'),
        #                      ('remove-slot', 'Remove a slot from the allocator server')]

        # # extract only the command names for argparse choices
        # allocator_commands = [cmd[0] for cmd in allocator_choices]

        # # manually add help argument since add_help=False
        # allocator_parser.add_argument("-h", "--help", 
        #                               action="help", 
        #                               help="Show the help information")
        
        # allocator_parser.add_argument('command',
        #                               choices=allocator_commands,  # Only command names
        #                               help='The command to run',
        #                               metavar='COMMAND')
        
        # allocator_parser.add_argument('--server', 
        #                               help='Server URL for add/remove commands.')
        
        if not args:
            allocator_parser.print_help()
            raise SystemExit(0)

        parsed_args, remaining_args = allocator_parser.parse_known_args(args)
        servers = self.load_servers()
        
        
        if parsed_args.command == 'add':
            name = parsed_args.name
            url = parsed_args.url
            if name not in servers:
                servers[name] = {"url": url}
                self.save_servers(servers)
                rich.print(f"[green]Server added: {parsed_args.name} -> {parsed_args.url}[/green]")
            else:
                rich.print(f"[yellow]Server already exists: {parsed_args.name}[/yellow]")

        elif parsed_args.command == 'remove':
            name = parsed_args.name
            if name in servers:
                del servers[name]
                self.save_servers(servers)
                rich.print(f"[green]Server removed: {parsed_args.name}[/green]")
            else:
                rich.print(f"[red]Server not found: {parsed_args.name}[/red]")

        elif parsed_args.command == 'list':
            if servers:
                rich.print("[blue]Configured servers:[/blue]")
                for name, info in servers.items():
                    rich.print(f" - {name}: {info.get('url', 'N/A')}")
            else:
                rich.print("[yellow]No servers configured.[/yellow]")

        elif parsed_args.command == 'search':
            if not parsed_args.server:
                rich.print("[red]Error: --server is required for search.[/red]")
                raise SystemExit(1)

            search_filters = {}
            if parsed_args.platform:
                search_filters["platform"] = parsed_args.platform
            if parsed_args.description:
                search_filters["description"] = parsed_args.description
            if parsed_args.tags:
                search_filters["tags"] = parsed_args.tags

            response = self.send_request("POST", f"{parsed_args.server}/list_slots", search_filters)

            if response and "slots" in response:
                slots = response["slots"]
                if slots:
                    rich.print("[blue]Matching slots:[/blue]")
                    for slot in slots:
                        rich.print(f" - {slot['rackName']} / {slot['slotName']} - {slot['description']} - Tags: {', '.join(slot['tags'])}")
                else:
                    rich.print("[yellow]No matching slots found.[/yellow]")
            else:
                rich.print("[red]Error retrieving slots.[/red]")

        elif parsed_args.command == 'add-slot':
            self._add_slot(parsed_args.server, remaining_args)

        elif parsed_args.command == 'update-slot':
            self._update_slot(parsed_args.server, remaining_args)

        elif parsed_args.command == 'remove-slot':
            self._remove_slot(parsed_args.server, remaining_args)


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
    
    def _add_slot(self, server, args: list):
        """
        Add a new slot to the allocator server.

        Args:
            args (list): Command-line arguments.
        """
        add_slot_parser = self._subparsers.add_parser('add-slot')
        add_slot_parser.add_argument('--rackName', required=True, help='Rack name of the slot.')
        add_slot_parser.add_argument('--slotName', required=True, help='Slot name.')
        add_slot_parser.add_argument('--description', help='Description of the slot.')
        add_slot_parser.add_argument('--tags', nargs='+', help='Tags for the slot.')
        add_slot_parser.add_argument('--platform', required=True, help='Platform associated with the slot.')
        add_slot_parser.add_argument('--state', choices=['free', 'allocated'], default='free', help='State of the slot.')
        add_slot_parser.add_argument('--owner_email', help='Owner email (if allocated).')

        parsed_args = add_slot_parser.parse_args(args)

        if not server or not parsed_args.rackName or not parsed_args.slotName or not parsed_args.platform:
            rich.print("[red]Error: --server, --rackName, --slotName, and --platform are required for add-slot.[/red]")
            raise SystemExit(1)
        
        payload = {
            "rackName": parsed_args.rackName,
            "slotName": parsed_args.slotName,
            "description": parsed_args.description or "",
            "tags": parsed_args.tags if parsed_args.tags else [],
            "platform": parsed_args.platform or "",
            "state": parsed_args.state,
            "owner_email": parsed_args.owner_email or None,
        }

        response = self.send_request("POST", f"{parsed_args.server}/add_slot", payload)
        
        if response:
            rich.print(f"[green]Slot added successfully: {response}[/green]")

    def _update_slot(self, server, args: list):
        """
        Update an existing slot in the allocator server.

        Args:
            args (list): Command-line arguments.
        """
        update_slot_parser = self._subparsers.add_parser('update-slot')
        update_slot_parser.add_argument('--slot_id', required=True, type=int, help='ID of the slot to update.')
        update_slot_parser.add_argument('--rackName', help='New rack name.')
        update_slot_parser.add_argument('--slotName', help='New slot name.')
        update_slot_parser.add_argument('--description', help='Updated description of the slot.')
        update_slot_parser.add_argument('--tags', nargs='+', help='Updated tags for the slot.')
        update_slot_parser.add_argument('--platform', help='Updated platform associated with the slot.')
        update_slot_parser.add_argument('--state', choices=['free', 'allocated'], help='Updated state of the slot.')
        update_slot_parser.add_argument('--owner_email', help='Updated owner email.')

        parsed_args = update_slot_parser.parse_args(args)

        if not server or not args.slot_id:
            rich.print("[red]Error: --server and --slot_id are required for update-slot.[/red]")
            raise SystemExit(1)

        if not any([parsed_args.rackName, parsed_args.slotName, parsed_args.description, parsed_args.tags,
                    parsed_args.platform, parsed_args.state, parsed_args.owner_email]):
            rich.print("[red]Error: At least one field must be provided for update.[/red]")
            sys.exit(1)

        # Required fields
        payload = {
            "slot_id": parsed_args.slot_id,
            "server": parsed_args.server
        }

        # Optional fields
        optional_fields = ["rackName", "slotName", "description", "tags", "platform", "state", "owner_email"]

        for field in optional_fields:
            value = getattr(parsed_args, field)
            if value is not None:
                payload[field] = value

        response = self.send_request("POST", f"{parsed_args.server}/update_slot", payload)

        if response:
            rich.print(f"[green]Slot updated successfully: {response}[/green]")

    def _remove_slot(self, server, args: list):
        """
        Remove a slot from the allocator server.

        Args:
            args (list): Command-line arguments.
        """
        remove_slot_parser = self._subparsers.add_parser('remove-slot')
        remove_slot_parser.add_argument('--slot_id', required=True, type=int, help='ID of the slot to remove.')

        parsed_args = remove_slot_parser.parse_args(args)

        if not server or not parsed_args.slot_id:
            rich.print("[red]Error: --server and --slot_id are required for remove-slot.[/red]")
            raise SystemExit(1)

        payload = {"slot_id": parsed_args.slot_id}
        response = self.send_request("POST", f"{parsed_args.server}/delete_slot", payload)

        if response:
            rich.print(f"[green]Slot removed successfully: {response}[/green]")

if __name__ == '__main__':
    import sys
    XTSAllocatorClient().run(sys.argv[1:])
