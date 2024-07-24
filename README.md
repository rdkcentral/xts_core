<div style="text-align:center"><img src="docs/images/XTS_Logo_250.png"/></div>

# XTS

**X** **T**est **S**uite

XTS is a CLI tool designed to simplify the usage of management and exection of tests for developers.

## Installatation

Run the [install.sh](install.sh) script.
```
./install.sh
```

## Usage

After installation `xts` will be available as a command. This will pick up any file with the extenstion `.xts` and try to use it as it's config.
The layout of the file dictates the commands that become available to use.

**To check which commands are available run `xts --help`**


## Documentation

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

## Contributing

See contributing file: [CONTRIBUTING.md](CONTRIBUTING.md)

## License

See license file: [LICENSE](LICENSE)