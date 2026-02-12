# XTS Repository Analyzer

AI-powered tool to analyze git repositories **and remote HTTP/HTTPS codebases** and generate XTS configuration files with assistance from AI models.

## Overview

The XTS Repository Analyzer (`xts analyze`) scans local git repositories **or remote HTTP URLs** to detect build systems, test frameworks, and common development workflows, then generates structured prompts that can be used with AI assistants (Claude, ChatGPT, Gemini, GitHub Copilot) to create complete `.xts` configuration files.

## Features

- 🔍 **Automatic Detection**: Finds build systems (Makefile, npm, pip, cargo, etc.)
- 🧪 **Test Framework Discovery**: Identifies pytest, jest, mocha, and other test runners
- 📋 **Command Extraction**: Pulls commands from README, package.json, Makefile
- 🤖 **AI-Ready Prompts**: Generates structured prompts for AI assistants
- 📊 **Multiple Output Formats**: Human-readable, JSON, or AI prompt
- 🌐 **Language Support**: Python, JavaScript/TypeScript, Go, Rust, C/C++, Java, Ruby
- 🌍 **Remote Analysis**: Analyze GitHub, GitLab, or any HTTP-accessible codebase
- 💾 **Smart Caching**: Temporarily downloads remote repos for analysis

## Usage

### Basic Analysis (Local)

Analyze current directory and display AI prompt:

```bash
xts analyze .
```

### Analyze Remote Repository (GitHub)

Analyze a GitHub repository via HTTPS:

```bash
xts analyze https://github.com/user/repo
```

Analyze and save prompt:

```bash
xts analyze https://github.com/user/repo --output prompt.txt
```

### Analyze Remote Repository (GitLab)

```bash
xts analyze https://gitlab.com/user/project --verbose
```

### Analyze Generic HTTP Server

For code hosted on a generic HTTP server:

```bash
xts analyze https://example.com/code/ --output prompt.txt
```

The analyzer will attempt to fetch common files (README, package.json, Makefile, etc.)

### Save AI Prompt to File (Local or Remote)

```bash
xts analyze . --output ai_prompt.txt
xts analyze https://github.com/user/repo --output ai_prompt.txt
```

Then copy the content and paste into your AI assistant of choice.

### Verbose Analysis

Show detailed detection results:

```bash
xts analyze . --verbose
```

### JSON Output

Get machine-readable analysis:

```bash
xts analyze . --json
```

### Analyze Remote Repository

```bash
# Clone first, then analyze
git clone https://github.com/user/repo
xts analyze repo/ --output repo_prompt.txt
```

**OR analyze directly via HTTP (no git clone needed):**

```bash
# Analyze GitHub repository directly
xts analyze https://github.com/user/repo --output prompt.txt

# Analyze GitLab repository
xts analyze https://gitlab.com/user/project --verbose

# Analyze code on generic HTTP server
xts analyze https://example.com/code/ --output prompt.txt
```

The analyzer will automatically:
- Try a shallow clone first (`git clone --depth 1 --single-branch`)
- Fall back to API/file fetching when clone is unavailable
- Cache files in a temporary directory
- Clean up after analysis completes

## What Gets Detected

### Build Systems
- **Make**: Makefile targets
- **npm/yarn**: package.json scripts
- **pip**: setup.py, requirements.txt
- **Poetry**: pyproject.toml
- **Cargo**: Cargo.toml (Rust)
- **Gradle**: build.gradle (Java)
- **Maven**: pom.xml (Java)
- **CMake**: CMakeLists.txt (C/C++)

### Test Frameworks
- pytest (Python)
- jest (JavaScript)
- mocha (JavaScript)
- unittest (Python)
- cargo test (Rust)
- go test (Go)

### Documentation
- README.md command extraction
- Code block parsing
- Command-line examples

### CI/CD
- GitLab CI
- Travis CI
- Jenkins
- CircleCI

Note: GitHub Actions is intentionally excluded from analyzer detection by policy.

## Example Workflow

### Step 1: Analyze Repository

```bash
cd my-project
xts analyze . --output ai_prompt.txt
```

Output:
```
✓ AI prompt saved to: ai_prompt.txt

You can now:
  1. Copy the prompt from ai_prompt.txt
  2. Paste it into Claude/ChatGPT/Gemini/Copilot
  3. Save the generated .xts file
  4. Add it: xts alias add myproject <generated>.xts
```

### Step 2: Use AI to Generate XTS File

Open the prompt in your AI assistant:

```bash
# Option 1: Claude (https://claude.ai)
cat ai_prompt.txt  # Copy and paste

# Option 2: GitHub Copilot Chat
# Open ai_prompt.txt in VS Code and ask Copilot to generate from it

# Option 3: ChatGPT (https://chat.openai.com)
# Paste the prompt content
```

### Step 3: Save and Use Generated XTS

The AI will generate a complete `.xts` file. Save it as `myproject.xts` and add it:

```bash
xts alias add myproject myproject.xts
xts myproject --help
```

## Supported AI Assistants

### Claude (Anthropic)
- URL: https://claude.ai
- Best for: Detailed, structured outputs
- Tip: Works great with long context prompts

### ChatGPT (OpenAI)
- URL: https://chat.openai.com
- Best for: Quick iterations and conversational refinement
- Tip: Use GPT-4 for better XTS structure

### Gemini (Google)
- URL: https://gemini.google.com
- Best for: Code understanding and generation
- Tip: Can handle complex project structures

### GitHub Copilot Chat
- Available in: VS Code, Visual Studio, JetBrains IDEs
- Best for: In-editor workflow
- Tip: Reference the prompt file directly in chat

## Example Analysis Output

### Verbose Mode

```bash
$ xts analyze . --verbose

======================================================================
  Repository Analysis
======================================================================

Path: /home/user/myproject
Language: python
Build System: None detected
Test Framework: pytest
Package Manager: None detected
CI/CD: GitLab CI

Package Scripts: 5 found
  • build: python setup.py build
  • test: pytest
  • lint: pylint src/
  • format: black src/
  • docs: sphinx-build docs/ build/

Makefile Targets: 3 found
  • install: make install
  • test: make test
  • clean: make clean

README Commands: 12 found
  • python setup.py install
  • pip install -r requirements.txt
  • pytest tests/
  • make docs
  • python -m myproject
  ... and 7 more

======================================================================
```

### AI Prompt Format

The generated prompt includes:

1. **Repository Context**
   - Path, language, build system
   - Test framework, package manager
   - CI/CD configuration

2. **Discovered Commands**
   - Package manager scripts
   - Makefile targets
   - README examples

3. **Generation Instructions**
   - XTS schema requirements
   - Best practices
   - Command structure guidelines

4. **Output Format Requirements**
   - YAML structure
   - Command organization
   - Documentation standards

## Advanced Usage

### Custom Prompt Templates

You can modify the generated prompt by editing the analyzer:

```python
# Edit: xts_core/xts_repo_analyzer.py
# Modify: RepoAnalyzer.generate_ai_prompt()
```

### Integration with AI APIs (Future)

Future versions may support direct API integration:

```bash
# Planned for future release
xts analyze . --ai claude --api-key $CLAUDE_API_KEY --auto-generate
```

This would automatically:
1. Analyze repository
2. Generate prompt
3. Call AI API
4. Save generated .xts file
5. Add alias

## Troubleshooting

### No Commands Detected

**Problem**: Analyzer finds no build commands or scripts.

**Solution**: Ensure your project has one of:
- README.md with code examples
- package.json with scripts
- Makefile with targets
- Standard project structure

### Incomplete Analysis

**Problem**: Missing commands or incorrect detection.

**Solution**: 
- Add commands to README in code blocks
- Use standard file naming (Makefile, package.json, etc.)
- Run with `--verbose` to see what was detected

### AI Generates Invalid YAML

**Problem**: Generated .xts file has syntax errors.

**Solution**:
- Validate: `xts validate generated.xts`
- Ask AI to fix: "The YAML has syntax errors at line X, please fix"
- Check schema: Ensure `schema_version: "1.0"` is present

## Examples

### Python Project

```bash
# Repository structure:
# - setup.py
# - requirements.txt
# - pytest.ini
# - README.md

xts analyze . --output python_prompt.txt
# Detects: pip, pytest, setup.py commands
```

### Node.js Project

```bash
# Repository structure:
# - package.json (with scripts: build, test, start)
# - jest.config.js
# - README.md

xts analyze . --output node_prompt.txt
# Detects: npm scripts, jest, build commands
```

### Makefile-based C Project

```bash
# Repository structure:
# - Makefile
# - CMakeLists.txt
# - README.md

xts analyze . --output c_prompt.txt
# Detects: make targets, cmake, compiler commands
```

## Tips and Best Practices

### For Best Results

1. **Document Your Commands**: Add command examples to README
2. **Use Standard Conventions**: package.json, Makefile, etc.
3. **Organize by Workflow**: Build → Test → Run → Deploy
4. **Include Help Text**: Add descriptions to commands
5. **Test Generated Files**: Always run `xts validate` after AI generation

### AI Prompt Engineering

When pasting into AI assistants:

- **Be Specific**: Add context about your project goals
- **Iterate**: Ask for refinements if first result isn't perfect
- **Request Examples**: Ask AI to include usage examples
- **Specify Style**: Request color schemes, naming conventions
- **Ask for Documentation**: Include --help text for commands

### Workflow Integration

```bash
# 1. Analyze
xts analyze . --output prompt.txt

# 2. Generate with AI
# (paste prompt into Claude/GPT)

# 3. Validate
xts validate generated.xts

# 4. Test
xts alias add test generated.xts
xts test --help

# 5. Commit
git add generated.xts
git commit -m "Add: XTS configuration for project workflow"
```

## Contributing

To improve the analyzer:

1. Add new build system detection in `xts_repo_analyzer.py`
2. Enhance prompt templates
3. Add language-specific parsers
4. Improve CI/CD detection

## Related Documentation

- [XTS Schema](../docs/SCHEMA.md)
- [XTS Wizard](../docs/WIZARD.md)
- [XTS Validation](../docs/VALIDATION.md)
- [Creating XTS Files](../docs/CREATING_XTS.md)
