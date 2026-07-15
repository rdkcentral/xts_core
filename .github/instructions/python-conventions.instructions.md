---
description: "Use when editing Python source in src/xts_core, adding CLI behavior, extending alias management, or implementing plugins. Covers project-specific Python conventions and library usage."
applyTo: "src/**/*.py"
---

# Python Conventions

- Preserve the existing Apache 2.0 file header when editing or creating Python source files.
- Add a module docstring for new modules and keep public function or class docstrings concise and concrete.
- Prefer project helpers from `xts_core.utils` for user-facing output instead of raw `print()`.
- Follow the existing CLI style: keep argument parsing explicit, keep validation close to the command entrypoint, and avoid hidden side effects.
- Keep plugin implementations under `src/xts_core/plugins/` and subclass `BaseXTSPlugin` when adding new plugins.
- Reuse the project's current libraries and patterns before introducing new dependencies. In particular, stay consistent with `argparse`, `yaml`, `requests`, and `rich` usage already present in the codebase.
- Keep functions focused and local. Prefer straightforward control flow over indirection.