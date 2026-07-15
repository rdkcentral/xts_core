---
description: "Use when adding or updating pytest coverage, CLI tests, alias tests, or plugin tests in the test suite. Covers fixtures, mocking, and repository test patterns."
applyTo: "test/**/*.py"
---

# Test Conventions

- Write tests with `pytest` and the existing fixture style used in the `test/` directory.
- Use `tmp_path` for temporary files and directories instead of writing into real user locations.
- Use `monkeypatch` to isolate environment-dependent behavior such as `HOME` and XTS cache paths.
- Mock external systems and network calls with `unittest.mock.patch` or pytest fixtures so tests stay deterministic.
- Keep tests narrow and behavior-focused. Name them for the observable behavior being validated.
- When adding coverage for a module, prefer extending the nearest existing test file unless a new file gives a clearer split.