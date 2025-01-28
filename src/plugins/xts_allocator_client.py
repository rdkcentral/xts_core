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
        return cls._positional_args

    @property
    def provided_positionals(cls):
        return list(map(lambda x: x[0] if isinstance(x,tuple) else x, cls.provided_args))

    @staticmethod
    def send_request(method, url, data=None):
        try:
            response = requests.request(method, url, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            rich.print(f"[red]Error during request: {e}[/red]")
            return None

    @staticmethod
    def load_servers():
        if os.path.exists(XTSAllocatorClient.CONFIG_FILE):
            with open(XTSAllocatorClient.CONFIG_FILE, 'r') as file:
                return yaml.safe_load(file) or {}
        return {}

    @staticmethod
    def save_servers(servers):
        with open(XTSAllocatorClient.CONFIG_FILE, 'w') as file:
            yaml.safe_dump(servers, file)

    def run(self, args: list):
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
        allocate_parser = self._subparsers.add_parser('allocate')
        allocate_parser.add_argument('--id', 
                                     dest='id', 
                                     help='Slot ID to allocate.')
        allocate_parser.add_argument('--platform', 
                                     dest='platform', 
                                     help='Platform required.')
        allocate_parser.add_argument('--tags', 
                                     dest='tags', 
                                     nargs='+', 
                                     help='Search tags.')
        allocate_parser.add_argument('--server', 
                                     dest='server', 
                                     required=True, 
                                     help='Allocator server address.')
        parsed_args = allocate_parser.parse_args(args)

        payload = {"id": parsed_args.id, "platform": parsed_args.platform, "tags": parsed_args.tags}
        response = self.send_request("POST", f"{parsed_args.server}/allocate", payload)
        if response:
            rich.print(f"[green]Slot allocated successfully: {response}[/green]")

    def _allocator(self, args: list):
        allocator_parser = self._subparsers.add_parser('allocator', add_help=False)
        allocator_choices = [('list', 'List all known allocators'),
                             ('add', 'Add an allocator server'),
                             ('remove', 'Remove an allocator server')]
        allocator_parser.add_argument('command',
                                      action='store',
                                      help='The command to run',
                                      choices=allocator_choices,
                                      default=None,
                                      metavar='COMMAND')
        allocator_parser.add_argument('--server', 
                                      help='Server URL for add/remove commands.')
        
        # allocator_parser.usage =  add_choices_to_help(allocator_parser.format_help(),
        #                                               'COMMAND',
        #                                               allocator_choices).replace('usage: ','')
        # parsed_args, remaining_args = allocator_parser.parse_known_args(args)
        
        parsed_args = allocator_parser.parse_args(args)
        servers = self.load_servers()
        
        # print('allocator ' + ' '.join(args))
        
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
