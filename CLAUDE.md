# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

QuickThumb is a Python library for programmatic thumbnail generation. See [README.md](README.md) for features and examples, [DESIGN.md](DESIGN.md) for API specifications and design principles.

## Project Structure

```
.
├── CLAUDE.md
├── DESIGN.md
├── LICENSE
├── README.md
├── pyproject.toml
├── quickthumb
│   └── __init__.py
├── tests
│   ├── __init__.py
│   ├── test_background_layers.py
│   ├── test_canvas_creation.py
└── uv.lock
```

## Development Commands

### Setup
```bash
# Install dependencies
uv sync
```

### Testing
```bash
# Run all tests
uv run pytest tests/ -v

# Run single test file
uv run pytest tests/test_canvas_creation.py -v

# Run specific test
uv run pytest tests/test_canvas_creation.py::TestCanvasCreation::test_should_create_canvas_with_explicit_dimensions -v

# Run with coverage report
uv run pytest tests/ --cov=quickthumb --cov-report=html
```

### Code Quality
```bash
# Type checking
uv run ty quickthumb/

# Linting
uv run ruff check quickthumb/

# Auto-fix linting issues
uv run ruff check --fix quickthumb/

# Format code
uv run ruff format quickthumb/
```

## Architecture

### Single-Module Design

Currently implemented in `quickthumb/__init__.py` (~120 lines). May be split into modules as it grows.

### Layer Stack Model

Layers are appended to `Canvas._layers` in call order and rendered sequentially:
1. Background layers (stackable with blend modes)
2. Text layers
3. Decoration layers

### Dual API

Both Python method chaining and JSON configuration map to the same internal `Canvas._layers` structure.

## Testing Philosophy

Follows **strict TDD** as defined in `.claude/agents/tdd-implementer.md`:
- Self-explanatory code (no "what"/"how" comments)
- Black-box testing (public API only)
- Green → Refactor cycle

Test naming: `test_should_{expected_behavior}_{optional_context}`
