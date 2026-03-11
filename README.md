<div style="text-align:center"><img src="docs/images/XTS_Logo_250.png"/></div>

# XTS

**eXtendable Task Syntax**

XTS is a flexible and declarative command orchestration system designed to simplify and unify how engineers run tests, build software, and automate routine tasks in embedded development environments. It replaces ad-hoc scripts with structured, reusable, and readable command definitions written in YAML.

By enabling users to define command groups and actions in .xts files, XTS brings consistency and clarity to complex command workflows — making development and testing easier to manage and less error-prone.
---

<details>
<summary style="font-weight:bold;font-size:large;">Contents</summary>

* [Why XTS](#why-xts)
  * [Key Features](#key-features)
    * [Other Features](#other-features)
    * [Planned Features](#planned-features)
* [Use Cases](#use-cases)
* [Installation](#installation)
  * [Installation Requirements](#installation-requirements)
  * [Installation Commands](#installation-commands)
* [Getting Started](#getting-started)
  * [Download the example .xts file](#download-the-example-.xts-file)
  * [Run a simple command](#run-a-simple-command)
  * [Run a command with arguments](#run-a-command-with-arguments)
  * [Finally try a list command](#finally-try-a-list-command)
  * [Try the remaining commands](#try-the-remaining-commands)
  * [Write a custom .xts file](#write-a-custom-.xts-file)
* [Learning XTS](#learning-xts)
  * [Interactive Tutorial](#interactive-tutorial)
  * [Built-in Manual](#built-in-manual)
* [How It Works](#how-it-works)
* [Contributing](#contributing)
* [License](#license)
</details>

---

## Why XTS

- **Unified Command Interface**: One consistent way to run test, build, and utility commands.

- **Human-Readable Configuration**: YAML format makes it easy to define, review, and update command logic.

- **Structured and Discoverable**: No need to memorize scripts or command sequences — just run `xts --help` to see what’s available.

- **Easy to Extend**: Add new commands or workflows by simply editing or adding .xts files.

- **Reduces Errors**: Encourages reuse of tested command patterns, reducing manual mistakes.

### Key Features

- **Command Discovery and Management**: XTS provides a powerful and flexible way to discover and manage your command definitions.<br>
XTS currently discovers commands from .xts files located in your **current working directory**.

- **Declarative YAML Configuration**: Define commands in a portable and version-controlled way.

#### Other Features

- **Command Grouping**: Organize commands into logical sections like run, build, and setup.

- **CLI Access**: Use xts <group> <command> to execute defined commands directly.

- **Developer-Focused**: Designed for local workflows — nothing extra required to get started.

- **Environment Resource Awareness**: Can work with external tools to allocate or prepare hardware for testing (optional).


#### Planned Features

- **Remote Config Support**: XTS supports `.xts` files hosted on remote HTTP/HTTPS URLs and GitHub repositories. See [Working with Aliases](#working-with-aliases) for details.

## Use Cases

- **Embedded Testing**: Run hardware or software tests across devices or setups.

- **Build Automation**: Standardize how code is compiled or packaged.

- **System Utilities**: Automate setup tasks like logging, flashing, or cleanup routines.

- **Developer Workflows**: Save time with shortcuts for repetitive development commands.

## Installation

### Installation Requirements
- Python 3.10 or above

> *Currently only the Linux operating system is supported by XTS*

### Installation Commands

XTS can be installed with the following commands:
```
pip install git+ssh://git@github.com/rdkcentral/xts_core.git@master
xts-install
```
<details>
<summary style="font-weight:bold">On Linux</summary>

After installation is complete the `xts` binary can be found in the users home directory under `.xts/bin/`. This will need adding to the PATH variable. The below command will do this:
```sh
export PATH="$HOME/.xts/bin:$PATH"
```
> This can be made permanent by adding the above command as a line in the users .profile or .rc file e.g.
> ```sh
>echo "export PATH=\"$HOME/.xts/bin:\$PATH\"" >> ~/.bashrc
>```
</details>


## Getting Started

After installation, `xts` will be available as a command. Command definitions from  .xts files found in your current working directory will be instantly available.

### Download the example .xts file
The below command will download the file into the current working directory.
```
curl https://raw.githubusercontent.com/rdkcentral/xts_core/refs/heads/master/examples/hello_world.xts -o hello_world.xts
```
> This file contains many example commands, all with comments describing how they work.

### Run a simple command
Since the first key in the `hello_world.xts` file is **run** this needs to be given as the first argument.<br>
Then the command key can be given. For this example use the `hello_world` key.
The full command will be:
```
xts run hello_world
```
This should cause `hello world` to be printed in the console.
> *If there more were more keys between run and hello_world, these would need to be given, sequentially, as arguments.*

### Run a command with arguments
The `echo_passthrough` key command in the file has `passthrough:true` listed in it's `params` section. This means that any extra arguments given after the command key will be substituted into the command run, replacing the `$@`.

To try this run the command below:
```
xts run echo_passthrough This is the example
```
This should print `This is the example` in the console.

### Finally try a list command
The `list` command key in the `hello_world.xts` uses a list in it's `command` section. This means that each of these command will be run individually, in sequence.<br>
Running the below command will result in multiple prints to the console.
```
xts run example list
```
This should cause the follow to print into the console:
```
These
are
separate
echoes
```

### Try the remaining commands

To check which commands are available run `xts --help`. This may need to be run, following other keys to follow the nesting in the file e.g.
```
xts run example --help
```

### Working with Aliases

XTS supports aliases for easy access to .xts files from any location:

```bash
# Add a local alias
xts alias add mytools ~/projects/tools.xts

# Add a remote alias
xts alias add demo https://example.com/demo.xts

# Add remote alias (proxy support is disabled)
xts alias add sky http://server:5000/allocator.xts

# Use the alias
xts mytools some_command

# List aliases
xts alias list

# Refresh an alias
xts alias refresh demo
```

**Proxy Support**: Proxy functionality is currently disabled in this version.

### Write a custom .xts file
Any file with the extension `.xts` will be picked up by the tool. Therefore, creating a file with this extension and filling it with valid command definitions will create a custom `.xts` file.

XTS is based on the [yaml_runner](https://github.com/rdkcentral/yaml_runner) library and follows its command definition structure. Key yaml_runner concepts used by XTS include hierarchical command dispatch, passthrough arguments (`$@` substitution), and fail-fast execution.

## Learning XTS

XTS includes built-in learning resources accessible directly from the command line.

### Interactive Tutorial

The `xts guide` command provides a progressive, hands-on tutorial system covering everything from basics to advanced topics:

```bash
# Start the tutorial
xts guide

# Browse specific modules
xts guide basics         # XTS fundamentals
xts guide commands       # Command definitions (simple, multiline, lists, args, options)
xts guide func           # Functions system (define, stdlib, usage)
xts guide structure      # .xts file structure (metadata, groups, nesting)
xts guide aliases        # Alias management (add, manage, remote)
xts guide tools          # Built-in tools (validate, create)
xts guide advanced       # Advanced topics (yaml_runner, tips)
xts guide quickref       # Quick reference card

# Dive into specific lessons
xts guide basics first   # Your first .xts file
xts guide commands args  # Arguments and passthrough
```

### Built-in Manual

The `xts manual` command displays a feature summary with links to detailed markdown documentation:

```bash
xts manual   # Feature overview and documentation index
```

For in-depth documentation, refer to the markdown files in the repository:

| Document | Description |
| -------- | ----------- |
| `README.md` | Overview, installation, getting started |
| `CHANGELOG.md` | Version history and release notes |
| `COMMAND_HISTORY.md` | Command recall and history features |
| `CONTRIBUTING.md` | Contribution guidelines |
| `docs/TAB_COMPLETION.md` | Bash tab completion setup and usage |
| `docs/install_command.md` | Installation command specification |
| `docs/PROXY_FEATURE.md` | Proxy support for remote aliases |
| `docs/REPO_ANALYZER.md` | Repository analyzer tool |
| `docs/HTTP_ANALYSIS.md` | HTTP remote repository analysis |

### Other Built-in Tools

```bash
xts validate myconfig.xts     # Validate .xts file schema and syntax
xts create newproject.xts      # Interactive wizard to create .xts files
```

## How It Works

XTS is built on the [yaml_runner](https://github.com/rdkcentral/yaml_runner) library, which handles YAML parsing and command execution. When you run an `xts` command:

1. **Configuration Loading** - XTS loads the `.xts` file (YAML format) and extracts command sections
2. **Function Injection** - Standard library functions (13 built-in formatters like `format_json`, `highlight_errors`) are merged with any user-defined functions
3. **Command Dispatch** - yaml_runner's hierarchical dispatch routes the command path (e.g., `xts myalias db backup`) to the correct nested command definition
4. **Argument Passthrough** - Commands with `passthrough: true` receive CLI arguments via `$@` substitution in the command string
5. **Execution** - Commands run in `/bin/sh` with fail-fast semantics (command lists stop on first failure)

## Contributing

See contributing file: [CONTRIBUTING.md](CONTRIBUTING.md)

## License

See license file: [LICENSE](LICENSE)
