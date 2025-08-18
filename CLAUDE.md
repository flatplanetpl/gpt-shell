# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python CLI tool that bridges AI models with the local filesystem through function calling. It provides an interactive chat interface where AI models can read, write, and search files within a designated working directory.

## Commands

### Setup and Run
```bash
./setup.sh              # Creates venv and installs dependencies
cp .env.example .env    # Copy environment template
./run.sh                # Main entry point with environment loading
```

### Debug Mode
```bash
DEBUG=1 DEBUG_FORMAT=text ./run.sh   # Text format logging
DEBUG=1 DEBUG_FORMAT=json ./run.sh   # JSON format logging
```

## Architecture

### Core Components
- **cli_assistant_fs.py**: Main entry point with OpenAI integration and function calling implementation
- **6 filesystem tools**: list_dir, read_file, read_file_range, write_file, list_tree, search_text
- **Security**: All operations sandboxed to WORKDIR via `within_workdir()` function
- **Context system**: clifs.context.json stores project-specific instructions and macros

### Key Design Patterns
1. **Function calling architecture**: Tools are defined with JSON schemas and executed through OpenAI's function calling
2. **Rate limit handling**: Automatic retry with exponential backoff for 429 and 5xx errors
3. **Memory management**: Conversation history trimming and tool result truncation
4. **Path security**: Strict path traversal protection with configurable ignore patterns

### Important Implementation Details
- The tool uses `max_completion_tokens` with fallback to `max_tokens` for API compatibility
- File operations have byte limits (MAX_BYTES_PER_READ) to prevent memory issues
- Shell commands are disabled by default (ALLOW_SHELL=0) for security
- Polish language interface throughout (prompts, responses, error messages)

## Development Guidelines

When modifying this codebase:
1. Maintain the security-first approach - never bypass `within_workdir()` checks
2. Preserve Polish language consistency in all user-facing strings
3. Test with both streaming and non-streaming modes
4. Ensure new tools follow the existing JSON schema pattern
5. Consider token limits when implementing new file operations