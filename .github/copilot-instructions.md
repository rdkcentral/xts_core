# Project Guidelines

## Project Context

XTS Core is a Python CLI for running declarative command workflows defined in `.xts` YAML files.
Prioritize the alias-based workflow described in [README.md](../README.md) over direct file execution.
Target Linux environments and Python 3.10+.

## Architecture

- Keep changes aligned with the existing split between CLI entrypoints, alias management, argument parsing, and plugins under `src/xts_core/`.
- Treat `.xts` files as the user-facing workflow definition format and Python modules as the execution/runtime layer.
- Keep plugin work isolated to `src/xts_core/plugins/` and follow the existing `BaseXTSPlugin` abstraction.
- Prefer small, local changes over broad refactors unless the task explicitly requires restructuring.

## Build And Test

- Set up a local environment with `python -m venv .venv`, activate it, then run `pip install -e .`.
- Install runtime dependencies from the project metadata rather than duplicating dependency definitions.
- Run the focused test slice first when possible, then `pytest test/` for broader validation.
- If a change affects CLI behavior, validate it with a targeted `pytest` run before expanding scope.

## Conventions

- Preserve the existing Apache 2.0 header format in Python source files.
- Use helpers from `xts_core.utils` for user-facing terminal output instead of adding ad hoc `print()` calls.
- Keep YAML examples and `.xts` fixtures readable, minimal, and consistent with [examples/hello_world.xts](/home/ubuntu/TEST/test-automation/xts_core/worktrees/bash_completion_AI/examples/hello_world.xts).
- Link contributors to [CONTRIBUTING.md](/home/ubuntu/TEST/test-automation/xts_core/worktrees/bash_completion_AI/CONTRIBUTING.md) for branch naming, issue linkage, and pull request workflow.