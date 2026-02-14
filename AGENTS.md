# Agent Guidelines

## Context Token Minimization
When implementing tools, prioritize minimal context usage:
- Return only essential information in structured JSON
- Keep responses concise
- Avoid unnecessary fields or verbose output

## API Documentation
- OpenAPI spec: `openapi.yaml`
- Refer to this spec for all available Lunch Money API endpoints and their schemas

## Running Python Commands
- Use `uv run python` for running Python commands instead of `python` directly
- Example: `uv run python -m py_compile main.py`
