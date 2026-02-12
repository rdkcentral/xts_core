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

"""XTS configuration file validator.

Validates .xts files against the JSON schema and performs additional checks
for command syntax, placeholder consistency, and best practices.
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any

import yaml
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False

try:
    from .utils import error, warning, success, info
except:
    from xts_core.utils import error, warning, success, info


class XTSValidator:
    """Validates XTS configuration files."""
    
    def __init__(self):
        """Initialize validator with schema."""
        schema_path = Path(__file__).parent / "xts_schema.json"
        if schema_path.exists():
            with open(schema_path) as f:
                self.schema = json.load(f)
        else:
            self.schema = None
            warning("Schema file not found - basic validation only")
    
    def validate_file(self, filepath: str, verbose: bool = False) -> Tuple[bool, List[str], List[str]]:
        """Validate an XTS file.
        
        Args:
            filepath: Path to .xts file
            verbose: Show detailed validation info
            
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        # Check file exists
        if not os.path.exists(filepath):
            errors.append(f"File not found: {filepath}")
            return False, errors, warnings
        
        # Check extension
        if not filepath.endswith('.xts'):
            warnings.append(f"File should have .xts extension")
        
        # Parse YAML
        try:
            with open(filepath) as f:
                config = yaml.load(f, SafeLoader)
        except yaml.YAMLError as e:
            errors.append(f"YAML parsing error: {e}")
            return False, errors, warnings
        
        if config is None:
            errors.append("Empty configuration file")
            return False, errors, warnings
        
        # JSON Schema validation
        if JSONSCHEMA_AVAILABLE and self.schema:
            try:
                jsonschema.validate(instance=config, schema=self.schema)
                if verbose:
                    info("✓ Schema validation passed")
            except jsonschema.ValidationError as e:
                errors.append(f"Schema validation failed: {e.message}")
                if e.path:
                    errors.append(f"  Location: {' -> '.join(str(p) for p in e.path)}")
        
        # Additional semantic validation
        self._validate_commands(config, errors, warnings, verbose)
        self._validate_functions(config, errors, warnings, verbose)
        self._validate_placeholders(config, errors, warnings, verbose)
        self._check_best_practices(config, errors, warnings, verbose)
        
        return len(errors) == 0, errors, warnings
    
    def _validate_commands(self, config: Dict, errors: List[str], warnings: List[str], verbose: bool):
        """Validate command definitions."""
        commands = config.get('commands', {})
        
        if not commands:
            warnings.append("No commands defined")
            return
        
        if verbose:
            info(f"Validating {len(commands)} command(s)")
        
        for cmd_name, cmd_def in commands.items():
            # Check command name
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', cmd_name):
                errors.append(f"Invalid command name '{cmd_name}' - must start with letter/underscore")
            
            # Check required fields
            if 'command' not in cmd_def:
                errors.append(f"Command '{cmd_name}' missing 'command' field")
                continue
            
            # Check command is not empty
            if not cmd_def['command'].strip():
                errors.append(f"Command '{cmd_name}' has empty command string")
            
            # Validate args
            if 'args' in cmd_def:
                seen_optional = False
                for i, arg in enumerate(cmd_def['args']):
                    arg_name = arg.get('name', f'arg_{i}')
                    
                    # Check required comes before optional
                    is_required = arg.get('required', True)
                    if not is_required:
                        seen_optional = True
                    elif seen_optional:
                        warnings.append(f"Command '{cmd_name}': Required arg '{arg_name}' after optional arg")
                    
                    # Check placeholder exists in command
                    placeholder = f"{{{{{arg_name}}}}}"
                    if placeholder not in cmd_def['command']:
                        warnings.append(f"Command '{cmd_name}': Arg '{arg_name}' not used in command")
    
    def _validate_functions(self, config: Dict, errors: List[str], warnings: List[str], verbose: bool):
        """Validate function definitions."""
        functions = config.get('functions', {})
        
        if not functions:
            if verbose:
                info("No functions defined")
            return
        
        if verbose:
            info(f"Validating {len(functions)} function(s)")
        
        for func_name, func_def in functions.items():
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', func_name):
                errors.append(f"Invalid function name '{func_name}'")
            
            if 'command' not in func_def:
                errors.append(f"Function '{func_name}' missing 'command' field")
    
    def _validate_placeholders(self, config: Dict, errors: List[str], warnings: List[str], verbose: bool):
        """Validate placeholder usage."""
        commands = config.get('commands', {})
        functions = config.get('functions', {})
        
        # Build set of defined functions (user-defined + standard library)
        from .standard_functions import get_standard_function_names
        func_names = get_standard_function_names() | set(functions.keys())
        
        for cmd_name, cmd_def in commands.items():
            # Find all placeholders in command
            command_str = cmd_def.get('command', '')
            placeholders = re.findall(r'\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}', command_str)
            
            # Build set of defined args
            arg_names = {arg['name'] for arg in cmd_def.get('args', [])}
            
            # Check each placeholder
            for placeholder in placeholders:
                if placeholder not in arg_names and placeholder not in func_names:
                    errors.append(
                        f"Command '{cmd_name}': Unknown placeholder '{{{{{placeholder}}}}}' "
                        f"(not in args or functions)"
                    )
            
            # Check formatter
            if 'formatter' in cmd_def:
                formatter = cmd_def['formatter']
                formatter_placeholders = re.findall(r'\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}', formatter)
                for placeholder in formatter_placeholders:
                    if placeholder not in func_names:
                        errors.append(
                            f"Command '{cmd_name}': Formatter references unknown function '{{{{{placeholder}}}}}'"
                        )
    
    def _check_best_practices(self, config: Dict, errors: List[str], warnings: List[str], verbose: bool):
        """Check best practices and style guidelines."""
        commands = config.get('commands', {})
        
        for cmd_name, cmd_def in commands.items():
            # Check for description
            if 'description' not in cmd_def:
                warnings.append(f"Command '{cmd_name}' missing description")
            
            # Check arg descriptions
            for arg in cmd_def.get('args', []):
                if 'description' not in arg:
                    warnings.append(f"Command '{cmd_name}': Arg '{arg['name']}' missing description")
            
            # Check for very long commands
            command_str = cmd_def.get('command', '')
            if len(command_str) > 500:
                warnings.append(
                    f"Command '{cmd_name}': Very long command ({len(command_str)} chars) - "
                    "consider using a script file"
                )
            
            # Check for inline python without python3
            if 'python -c' in command_str and 'python3 -c' not in command_str:
                warnings.append(f"Command '{cmd_name}': Use 'python3' instead of 'python' for compatibility")


def validate_command(filepath: str, verbose: bool = False, json_output: bool = False) -> int:
    """Validate an XTS file and print results.
    
    Args:
        filepath: Path to .xts file
        verbose: Show detailed validation info
        json_output: Output results as JSON
        
    Returns:
        Exit code (0 = valid, 1 = invalid)
    """
    validator = XTSValidator()
    is_valid, errors_list, warnings_list = validator.validate_file(filepath, verbose)
    
    if json_output:
        result = {
            "file": filepath,
            "valid": is_valid,
            "errors": errors_list,
            "warnings": warnings_list
        }
        print(json.dumps(result, indent=2))
    else:
        # Human-readable output
        print(f"\nValidating: {filepath}\n")
        
        if errors_list:
            error(f"✗ Found {len(errors_list)} error(s):")
            for err in errors_list:
                print(f"  • {err}")
            print()
        
        if warnings_list:
            warning(f"⚠ Found {len(warnings_list)} warning(s):")
            for warn in warnings_list:
                print(f"  • {warn}")
            print()
        
        if is_valid and not warnings_list:
            success(f"✓ Validation passed - file is valid!")
        elif is_valid:
            success(f"✓ Validation passed with {len(warnings_list)} warning(s)")
        else:
            error("✗ Validation failed")
    
    return 0 if is_valid else 1


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate XTS configuration files")
    parser.add_argument('file', help='Path to .xts file to validate')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed validation info')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    
    args = parser.parse_args()
    
    if not JSONSCHEMA_AVAILABLE:
        warning("jsonschema package not installed - install with: pip install jsonschema")
        print()
    
    exit_code = validate_command(args.file, args.verbose, args.json)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
