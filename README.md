
<div align="center">
  <img src="docs/images/XTS_Logo_250.png" alt="XTS Logo"/>
</div>


# XTS Core

**eXtendable Task Syntax (XTS)**

XTS is a flexible, declarative command orchestration system for embedded and developer workflows. It replaces ad-hoc scripts with structured, reusable, and readable command definitions written in YAML, making complex command workflows consistent, discoverable, and easy to maintain.

---

## Table of Contents

- [Why XTS?](#why-xts)
- [Features](#features)
- [Use Cases](#use-cases)
- [Installation](#installation)
- [Alias Management & Usage](#alias-management--usage)
- [Example .xts File](#example-xts-file)
- [Contributing](#contributing)
- [License](#license)

---

## Why XTS?

- **Unified Command Interface:** One consistent way to run test, build, and utility commands.
- **Human-Readable YAML:** Easy to define, review, and update command logic.
- **Discoverable & Structured:** No need to memorize scripts—`xts <alias> --help` shows all available commands for an alias.
- **Extensible:** Add new commands or workflows by editing or adding `.xts` files and managing aliases.
- **Reduces Errors:** Encourages reuse of tested command patterns, reducing manual mistakes.

## Features

- **Alias-Only Usage:** All XTS command execution is routed through an alias. Direct discovery of .xts files in the current directory is no longer supported.
- **Declarative YAML Configuration:** Define commands in portable, version-controlled `.xts` files.
- **Command Grouping:** Organize commands into logical sections (e.g., `run`, `build`).
- **CLI Access:** Use `xts <alias> <group> <command>` to execute defined commands directly.
- **Plugin Support:** Extend XTS with Python plugins (see `src/xts_core/plugins`).
- **Resource Awareness:** Integrates with external tools (e.g., Allocator Client) for hardware resource management.
- **Linux Support:** Designed for Linux environments (Python 3.10+ required).

## Use Cases

- **Embedded Testing:** Run hardware/software tests across devices or setups.
- **Build Automation:** Standardize how code is compiled or packaged.
- **System Utilities:** Automate setup tasks like logging, flashing, or cleanup routines.
- **Developer Workflows:** Save time with shortcuts for repetitive development commands.

## Installation

### Requirements
- Python 3.10 or above
- Linux OS

### Install Steps
```sh
pip install git+https://github.com/rdkcentral/xts_core.git@master
xts-install
```
After installation, the `xts` binary is placed in `$HOME/.xts/bin/`. Add this to your PATH:
```sh
export PATH="$HOME/.xts/bin:$PATH"
```
To make this permanent:
```sh
echo 'export PATH="$HOME/.xts/bin:$PATH"' >> ~/.bashrc
```

## Alias Management & Usage

All XTS usage is now via **aliases**. You must add an alias for each .xts file (local or remote) you want to use. Direct usage of .xts files in the current directory is not supported.

### Adding Aliases

- **From a local file:**
  ```sh
  xts alias /path/to/yourfile.xts [--name myalias]
  # or
  xts alias add /path/to/yourfile.xts [--name myalias]
  ```
- **From a remote URL:**
  ```sh
  xts alias https://example.com/yourfile.xts [--name myalias]
  # or
  xts alias add https://example.com/yourfile.xts [--name myalias]
  ```
- **From a directory (adds all .xts files in the directory):**
  ```sh
  xts alias /path/to/dir/ [--name prefix]
  # aliases will be named as prefix/filename
  ```

### Listing Aliases

```sh
xts alias list
```

### Removing an Alias

```sh
xts alias remove myalias
```

### Refreshing an Alias (re-download or re-copy from original source)

```sh
xts alias refresh myalias
```

### Using an Alias to Run Commands

Once an alias is added, use it as the first argument to XTS:

```sh
xts myalias <group> <command> [args...]
# Example (if your .xts file has a 'run' group and 'hello_world' command):
xts myalias run hello_world
```

To see available commands for an alias:
```sh
xts myalias --help
```

### Validate an .xts File

Use the built-in validator to check YAML syntax for an `.xts` file without running it:

```sh
xts validate /path/to/file.xts
```

This command reports syntax errors clearly and exits with code `0` for valid files or `1` for invalid files.

## Example .xts File

```yaml
run:
  hello_world:
    command: echo "hello world"
    description: Print hello world in stdout
  echo_passthrough:
    description: Print all arguments passed after echo_passthrough.
    command: echo $@
    params:
      passthrough: true
  example:
    description: Example of how nested commands work.
    nested:
      description: Run the nested command.
      command: echo "This is the nested command"
    list:
      description: Run a list of commands
      command:
        - echo "These"
        - echo "are"
        - echo "separate"
        - echo "echoes"
    list_passthrough:
      description: Run each command listed, substituting the extra args in.
      command:
        - echo "echo 1"
        - echo "$@"
        - echo "echo 2"
        - echo "$@"
      params:
        passthrough: true
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE).
