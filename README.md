<div style="text-align:center"><img src="docs/images/XTS_Logo_250.png"/></div>

# XTS

**X** **T**est **S**uite

XTS is a flexible and declarative command orchestration system designed to simplify and unify how engineers run tests, build software, and automate routine tasks in embedded development environments. It replaces ad-hoc scripts with structured, reusable, and readable command definitions written in YAML.

By enabling users to define command groups and actions in .xts files, XTS brings consistency and clarity to complex command workflows — making development and testing easier to manage and less error-prone.

### Why XTS ###

- **Unified Command Interface**: One consistent way to run test, build, and utility commands.

- **Human-Readable Configuration**: YAML format makes it easy to define, review, and update command logic.

- **Structured and Discoverable**: No need to memorize scripts or command sequences — just run `xts --help` to see what’s available.

- **Easy to Extend**: Add new commands or workflows by simply editing or adding .xts files.

- **Reduces Errors**: Encourages reuse of tested command patterns, reducing manual mistakes.

### Key Features ###

- **Automatic Directory Scanning**: Discovers all .xts files within the current folder.

- **Declarative YAML Configuration**: Define commands in a portable and version-controlled way.

- **Grouped Commands**: Organize actions into logical sections like run, build, and setup.

- **CLI Access**: Use xts <group> <command> to execute defined actions directly.

- **Environment Resource Awareness**: Can work with external tools to allocate or prepare hardware for testing (optional).

- **Developer-Focused**: Designed for local workflows — nothing extra required to get started.


## Installatation

Run the [install.sh](install.sh) script.
```
./install.sh
```

## Usage

After installation, `xts` will be available as a command. This will pick up any file with the extenstion `.xts` and try to use it as its config.
The layout of the file dictates the commands that become available to use.

**To check which commands are available run `xts --help`**


## Example Workflow

Here is an example of an xts yaml config that will run with xts [hello_world.xts](examples/hello_world.xts). It has comments explaining how the sections are used.
This config can be tested with the xts by running the following commands in the examples directory.

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

## Use Cases ##

- **Embedded Testing**: Run hardware or software tests across devices or setups.

- **Build Automation**: Standardize how code is compiled or packaged.

- **System Utilities**: Automate setup tasks like logging, flashing, or cleanup routines.

- **Developer Workflows**: Save time with shortcuts for repetitive development commands.

## Contributing

See contributing file: [CONTRIBUTING.md](CONTRIBUTING.md)

## License

See license file: [LICENSE](LICENSE)