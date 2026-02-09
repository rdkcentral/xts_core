# XTS Core Test Coverage

## Overview

Comprehensive test suite for XTS enhancements including universal caching, validation infrastructure, and directory scanning features.

**Total Tests:** 61  
**Status:** ✓ All passing  
**Coverage:** 65% xts_alias.py, 78% xts_validator.py

## Test Suites

### 1. test_xts_alias_enhanced.py (341 lines, 35 tests)

Tests for universal caching system that stores all .xts files (local + remote) to `~/.xts/cache/`.

#### TestEnsureDirs (2 tests)
- ✓ Creates cache directory structure
- ✓ Creates parent directories for alias files

#### TestComputeFileHash (3 tests)
- ✓ Computes SHA256 hash correctly
- ✓ Different content produces different hashes
- ✓ Handles missing files gracefully

#### TestIsUrl (3 tests)
- ✓ Detects HTTP URLs
- ✓ Detects HTTPS URLs
- ✓ Identifies local paths correctly

#### TestFindXtsFiles (5 tests)
- ✓ Finds .xts files in single directory
- ✓ Recursive search finds nested files
- ✓ Non-recursive search only top-level files
- ✓ Handles empty directories
- ✓ Validates input is a directory

#### TestCacheLocalFile (3 tests)
- ✓ Caches local files to cache directory
- ✓ Preserves file content during caching
- ✓ Handles missing source files (SystemExit)

#### TestAddAlias (4 tests)
- ✓ Adds alias for local file with caching
- ✓ Creates metadata with source tracking
- ✓ Converts relative paths to absolute
- ✓ Fetches and caches remote URLs

#### TestListAliases (2 tests)
- ✓ Returns empty dict when no aliases
- ✓ Lists multiple aliases with cache paths

#### TestRemoveAlias (3 tests)
- ✓ Removes alias and cleans up cache file
- ✓ Removes metadata entry
- ✓ Handles non-existent aliases gracefully

#### TestCheckLocalUpdates (3 tests)
- ✓ Detects when file is up-to-date
- ✓ Detects when source file modified (mtime + hash)
- ✓ Detects when source file missing

#### TestRefreshAlias (3 tests)
- ✓ Refreshes cache from modified source
- ✓ Handles non-existent alias (SystemExit)
- ✓ Handles missing source file

#### TestCleanBrokenAliases (3 tests)
- ✓ Finds aliases with missing cache files
- ✓ Finds aliases with missing source files
- ✓ Respects user decline to remove

#### TestGetCachePath (3 tests)
- ✓ Generates unique paths based on content hash
- ✓ Includes alias name in path for readability
- ✓ Same source produces consistent path

### 2. test_xts_validator.py (351 lines, 26 tests)

Tests for .xts file validation against JSON Schema and semantic rules.

#### TestValidatorInit (2 tests)
- ✓ Loads schema from JSON file
- ✓ Handles missing schema gracefully

#### TestYamlParsing (4 tests)
- ✓ Validates correct YAML structure
- ✓ Detects invalid YAML syntax
- ✓ Handles empty files
- ✓ Handles missing files

#### TestCommandValidation (4 tests)
- ✓ Detects missing 'command' field
- ✓ Detects empty command strings
- ✓ Validates command name patterns (alphanumeric + underscore)
- ✓ Detects missing description field

#### TestArgumentValidation (2 tests)
- ✓ Detects required args after optional args
- ✓ Detects unused arguments (defined but not in command)

#### TestPlaceholderValidation (3 tests)
- ✓ Detects undefined placeholders in commands
- ✓ Validates function placeholders exist
- ✓ Detects undefined functions in formatters

#### TestFunctionValidation (2 tests)
- ✓ Detects missing 'command' field in functions
- ✓ Validates function name patterns

#### TestBestPractices (2 tests)
- ✓ Warns about long commands (>120 chars)
- ✓ Recommends python3 over python

#### TestFileExtension (1 test)
- ✓ Warns about missing .xts extension

#### TestValidateCommand (4 tests)
- ✓ CLI validates correct files
- ✓ CLI exits with code 1 for invalid files (SystemExit)
- ✓ JSON output mode works
- ✓ Verbose mode shows detailed output

## Key Features Tested

### Universal Caching System
- All .xts files cached to `~/.xts/cache/` (local + remote)
- Metadata tracking in `~/.xts/metadata.json`
- SHA256 hashing for change detection
- Update checking via mtime (local) and ETag/Last-Modified (remote)
- Cache cleanup for broken aliases

### Directory Scanning
- Recursive flag `-r` finds nested .xts files
- Non-recursive mode only scans top level
- Multiple files added in single command

### Validation Infrastructure
- JSON Schema validation for .xts structure
- Semantic validation (placeholder checking, arg ordering)
- Best practices checking (command length, python version)
- CLI with verbose and JSON output modes

### Error Handling
- SystemExit raised for user-facing errors
- Proper exception handling in tests with `pytest.raises`
- Graceful fallbacks for missing files

## Running Tests

```bash
# Run all tests
cd 3rdParty/xts_core/test
./run_tests.sh

# Run specific test file
pytest test_xts_alias_enhanced.py -v

# Run specific test class
pytest test_xts_alias_enhanced.py::TestCacheLocalFile -v

# Run with coverage
pytest --cov=../src/xts_core --cov-report=html
```

## Test Fixtures

### temp_xts_dir (test_xts_alias_enhanced.py)
- Patches cache and alias paths to temp directory
- Provides isolated environment for each test
- Auto-cleanup after test completes

### sample_xts_files (test_xts_alias_enhanced.py)
- Creates nested directory structure with .xts files
- Provides realistic test data
- Structure:
  ```
  root/
  ├── single.xts
  └── nested/
      ├── file1.xts
      └── file2.xts
  ```

### validator (test_xts_validator.py)
- Pre-loaded XTSValidator instance with schema
- Reused across all validation tests

### temp_xts_file (test_xts_validator.py)
- Factory fixture for creating temporary .xts files
- Accepts content string, returns file path
- Auto-cleanup after test

## Coverage Analysis

### xts_alias.py: 65% (196/303 lines)

**Well-covered:**
- File hashing and caching operations
- Alias management (add, list, remove)
- Update detection for local files
- Cache path generation

**Needs coverage:**
- Remote URL fetching (lines 241-268)
- HTTP header parsing for cache validation
- Error handling in network operations
- Concurrent access edge cases

### xts_validator.py: 78% (129/166 lines)

**Well-covered:**
- YAML parsing and schema validation
- Command and function validation
- Placeholder checking
- CLI entry point

**Needs coverage:**
- Detailed error message formatting (lines 272-287)
- Edge cases in best practices checking
- Schema loading error paths

## Future Test Additions

1. **Integration Tests**
   - End-to-end alias workflow (add → list → use → refresh → remove)
   - Multi-server scenarios for federation
   - Real HTTP requests with mock servers

2. **Performance Tests**
   - Large directory scanning (1000+ files)
   - Concurrent alias operations
   - Cache size limits and cleanup

3. **Wizard Tests**
   - Interactive creation workflow
   - CTRL-C save/resume functionality
   - Edit mode with existing files

4. **Network Tests**
   - HTTP/HTTPS URL fetching
   - ETag and Last-Modified handling
   - Timeout and retry logic
   - SSL certificate validation

## Notes

- Tests use `pytest.raises(SystemExit)` for CLI commands that exit on error
- Mock HTTP requests prevent actual network calls in tests
- Temp directories ensure test isolation
- Fixtures provide consistent test data across test methods
