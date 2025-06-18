<div style="text-align:center"><img src="docs/images/XTS_Logo_250.png"/></div>

# XTS

**eXtendable Task Syntax**

XTS is a flexible and declarative command orchestration system designed to simplify and unify how engineers run tests, build software, and automate routine tasks in embedded development environments. It replaces ad-hoc scripts with structured, reusable, and readable command definitions written in YAML.

By enabling users to define command groups and actions in .xts files, XTS brings consistency and clarity to complex command workflows — making development and testing easier to manage and less error-prone.

### Why XTS

- **Unified Command Interface**: One consistent way to run test, build, and utility commands.

- **Human-Readable Configuration**: YAML format makes it easy to define, review, and update command logic.

- **Structured and Discoverable**: No need to memorize scripts or command sequences — just run `xts --help` to see what’s available.

- **Easy to Extend**: Add new commands or workflows by simply editing or adding .xts files.

- **Reduces Errors**: Encourages reuse of tested command patterns, reducing manual mistakes.

### Key Features

- **Automatic Directory Scanning**: Discovers all .xts files within the current folder.

- **Declarative YAML Configuration**: Define commands in a portable and version-controlled way.

- **Grouped Commands**: Organize actions into logical sections like run, build, and setup.

- **CLI Access**: Use xts <group> <command> to execute defined actions directly.

- **Environment Resource Awareness**: Can work with external tools to allocate or prepare hardware for testing (optional).

- **Developer-Focused**: Designed for local workflows — nothing extra required to get started.

### Command Discovery and Management

XTS provides a powerful and flexible way to discover and manage your command definitions.

- **Current Behaviour**: XTS currently discovers commands from .xts files located in your **current working directory**.

- **Planned Remote Config Support**: In upcoming versions, XTS will introduce the ability to use XTS config files hosted in remote locations.

## Installatation

To install XTS, clone the repository and run the installation script:
```
git clone git@github.com:rdkcentral/xts_core.git
cd xts_core
./install.sh
```
The [install.sh](install.sh) script will set up XTS and, by default, populate your Command Registry with a core set of system commands.

## Usage

After installation, `xts` will be available as a command. It automatically merges command definitions from your **Command Registry** (if configured) with any .xts files found in your current working directory. This allows for a flexible hierarchy of global and project-specific commands.

**To check which commands are available run `xts --help`**


## Example Workflow

Here is an example of an XTS YAML config that will run with XTS [hello_world.xts](examples/hello_world.xts). It has comments explaining how the sections are used.
This config can be tested with the XTS by running the following commands in the `examples` directory.

### Example command #1

```sh
xts run hello_world
```
This will print the words "hello world".

### Example command #2

```sh
xts run list_demo me
```
This should give the below output:
```sh
Hello
me
Goodbye
me
```
*As the command in the config is using `$@` for the parameters, anything entered after `xts run list_demo` will be printed in place of the word "me".*

## Use Cases

- **Embedded Testing**: Run hardware or software tests across devices or setups.

- **Build Automation**: Standardize how code is compiled or packaged.

- **System Utilities**: Automate setup tasks like logging, flashing, or cleanup routines.

- **Developer Workflows**: Save time with shortcuts for repetitive development commands.

## Contributing

See contributing file: [CONTRIBUTING.md](CONTRIBUTING.md)

## License

See license file: [LICENSE](LICENSE)