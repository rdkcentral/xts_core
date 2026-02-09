#!/usr/bin/env python3
#** *****************************************************************************
# *
# * If not stated otherwise in this file or this component's LICENSE file the
# * following copyright and licenses apply:
# *
# * Copyright 2026 RDK Management
# *
# * Licensed under the Apache License, Version 2.0 (the "License");
# * you may not use this file except in compliance with the License.
# * You may obtain a copy of the License at
# *
# *
# http://www.apache.org/licenses/LICENSE-2.0
# *
# * Unless required by applicable law or agreed to in writing, software
# * distributed under the License is distributed on an "AS IS" BASIS,
# * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# * See the License for the specific language governing permissions and
# * limitations under the License.
# *
#* ******************************************************************************

"""XTS Tools Plugin - Commands for working with .xts files.

Provides:
- validate: Validate .xts file schema and syntax
- create: Interactive wizard to create new .xts files
- edit: Interactive editor for existing .xts files
"""

import sys
from pathlib import Path

try:
    from ..utils import info, error, success
    from ..xts_validator import validate_command
    from ..xts_wizard import XTSWizard
    from .base_plugin import BaseXTSPlugin as Plugin
except:
    from xts_core.utils import info, error, success
    from xts_core.xts_validator import validate_command
    from xts_core.xts_wizard import XTSWizard
    from xts_core.plugins.base_plugin import BaseXTSPlugin as Plugin


class XTSToolsPlugin(Plugin):
    """Plugin providing tools for managing .xts files."""
    
    def __init__(self):
        """Initialize the tools plugin."""
        super().__init__()
        self.provided_positionals = ['validate', 'create', 'edit']
        self.provided_args = []  # No args, only positionals
    
    def run(self, args: list):
        """Execute the appropriate tools command.
        
        Args:
            args: Command-line arguments starting with the command name
        """
        if not args:
            self._print_help()
            sys.exit(1)
        
        command = args[0]
        
        if command == 'validate':
            self._validate(args[1:])
        elif command == 'create':
            self._create(args[1:])
        elif command == 'edit':
            self._edit(args[1:])
        else:
            error(f"Unknown tools command: {command}")
            self._print_help()
            sys.exit(1)
    
    def _print_help(self):
        """Print help for tools commands."""
        print("\nXTS Tools - Manage .xts configuration files\n")
        print("Commands:")
        print("  validate <file>      Validate .xts file schema and syntax")
        print("                       Options: -v/--verbose, --json")
        print()
        print("  create <file>        Create new .xts file interactively")
        print("                       Options: --resume (resume from saved state)")
        print()
        print("  edit <file>          Edit existing .xts file interactively")
        print()
        print("Examples:")
        print("  xts validate myconfig.xts")
        print("  xts validate myconfig.xts -v")
        print("  xts create newproject.xts")
        print("  xts edit myconfig.xts")
        print("  xts create newproject --resume  # Resume after CTRL-C")
        print()
    
    def _validate(self, args: list):
        """Validate an .xts file."""
        if not args:
            error("File path required")
            print("\nUsage: xts validate <file> [-v|--verbose] [--json]")
            sys.exit(1)
        
        filepath = args[0]
        verbose = '-v' in args or '--verbose' in args
        json_output = '--json' in args
        
        exit_code = validate_command(filepath, verbose, json_output)
        sys.exit(exit_code)
    
    def _create(self, args: list):
        """Create a new .xts file interactively."""
        if not args:
            error("File path required")
            print("\nUsage: xts create <file> [--resume]")
            sys.exit(1)
        
        filepath = args[0]
        resume = '--resume' in args
        
        # Ensure .xts extension
        if not filepath.endswith('.xts'):
            filepath += '.xts'
        
        # Check if file already exists
        if Path(filepath).exists() and not resume:
            response = input(f"File '{filepath}' exists. Overwrite? (y/n): ").strip().lower()
            if response != 'y':
                info("Cancelled")
                sys.exit(0)
        
        wizard = XTSWizard(filepath, edit_mode=False)
        exit_code = wizard.run(resume=resume)
        sys.exit(exit_code)
    
    def _edit(self, args: list):
        """Edit an existing .xts file interactively."""
        if not args:
            error("File path required")
            print("\nUsage: xts edit <file>")
            sys.exit(1)
        
        filepath = args[0]
        
        if not Path(filepath).exists():
            error(f"File not found: {filepath}")
            sys.exit(1)
        
        wizard = XTSWizard(filepath, edit_mode=True)
        exit_code = wizard.run(resume=False)
        sys.exit(exit_code)
