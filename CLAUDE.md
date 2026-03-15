# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

QuickThumb is a Python library for programmatic thumbnail generation. See @README.md for features and API specifications, @specs/SPEC.md for planned features.

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

# Tests
uv run pytest [args]
```
