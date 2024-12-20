#!/usr/bin/env python3

import argparse
import rich

from yaml_runner import add_choices_to_help

class XTSAllocatorClient():
    _positional_args = [
        ('allocate', 'Request allocation of a slot.'),
        ('alloc', 'Alias for allocate.'),
        ('allocator', 'Make changes to the allocator server.'),
        ('deallocate', 'Free an allocated slot.'),
        ('dealloc', 'Alias of deallocate'),
        ('free', 'Alias of deallocate')
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

    def run(self, args: list):
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

    def _allocate_slot(self,args: list):
        allocate_parser = self._subparsers.add_parser('allocate')
        allocate_parser.add_argument('--id',
                                     dest='id',
                                     action='store',
                                     default=None,
                                     help='ID number of slot to allocate.',
                                     nargs=1)
        # --duration --server
        allocate_parser.add_argument('--platform',
                                     dest='platform',
                                     action='store',
                                     default=None,
                                     help='Platform of DUT required.',
                                     nargs=1)
        allocate_parser.add_argument('--tags',
                                     dest='tags',
                                     action='store',
                                     default=None,
                                     help='Search tags for matching slot. Requires --platform option.',
                                     nargs=argparse.REMAINDER)
        allocate_parser.add_argument('--server',
                                     dest='server',
                                     action='store',
                                     default=None,
                                     help='Address of allocator server.',
                                     nargs=1
                                     )
        if len(args) < 2:
            allocate_parser.print_help()
            raise SystemExit(1)
        parsed_args = allocate_parser.parse_args(args)
        if parsed_args.tags and not parsed_args.platform:
            allocate_parser.print_help()
            raise SystemExit(1)
        # TODO Format args into json and post to /allocate endpoint or requested server

    def _allocator(self,args: list):
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
        allocator_parser.usage =  add_choices_to_help(allocator_parser.format_help(),
                                                      'COMMAND',
                                                      allocator_choices).replace('usage: ','')
        parsed_args, remaining_args = allocator_parser.parse_known_args(args)
        print('allocator ' + ' '.join(args))

    def _deallocate_slot(self, args: list):
        deallocate_parser = self._subparsers.add_parser('deallocate')
        deallocate_parser.add_argument('--id',
                                       dest='id',
                                       action='store',
                                       default=None,
                                       help='ID number of slot free',
                                       nargs=1,
                                       type=int)
        parsed_args = deallocate_parser.parse_args(args)
        if parsed_args.id is None:
            rich.print('[red][bold]ID argument required.[/bold][/red]')
            deallocate_parser.print_help()
            raise SystemExit(1)
        # TODO: Format args into json and post to /deallocate endpoint or requested server

if __name__ == '__main__':
    import sys
    XTSAllocatorClient().run(sys.argv[1:])