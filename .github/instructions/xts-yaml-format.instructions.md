---
description: "Use when creating or editing .xts workflow files, examples, or YAML command definitions for XTS. Covers command structure, nesting, passthrough parameters, and formatting expectations."
applyTo: "**/*.xts"
---

# XTS YAML Format

- Follow the command layout shown in [examples/hello_world.xts](../../examples/hello_world.xts).
- Use top-level keys as command groups and nested keys as executable commands or subcommands.
- Provide a `description` for each runnable command so CLI help stays useful.
- Use `command` as either a single shell command string or a list of commands to run in sequence.
- Use `params.passthrough: true` only when the command is intended to forward extra CLI arguments.
- Keep YAML indentation to two spaces and do not use tabs.
- Ignore unrelated data structures unless the task explicitly requires documenting or validating ignored sections.