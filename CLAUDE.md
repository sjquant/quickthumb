# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

QuickThumb is a Python library for programmatic thumbnail generation. See @README.md for features, @DESIGN.md for API specifications.

## Project Structure

```
quickthumb/
├── canvas.py      # Canvas class with method chaining API
├── models.py      # Pydantic models (CanvasModel, BackgroundLayer, TextLayer, etc.)
├── font_cache.py  # Font loading and caching
└── errors.py      # Custom exceptions
tests/              # Tests follow pattern: test_{component}.py
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
