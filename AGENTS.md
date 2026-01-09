<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# Repository Guidelines

This document explains how to work productively in this repository.

## Project Structure & Modules

- `src/` – application and agent logic (core services, integrations).
- `tests/` – automated tests mirroring the layout of `src/`.
- `scripts/` – helper scripts for local tooling and maintenance.
- `config/` – environment, model, and service configuration.

When adding new modules, group related code under a meaningful subdirectory (for example, `src/agents/portfolio/`, `src/services/brokerage/`).

## Python & Tooling

- The current runtime is Python 3.9; new work should be compatible with 3.9 until the runtime is upgraded.
- Dependency resolution and virtualenv management should use `uv` configured with Python 3.13 (for example, `uv python pin 3.13`), even if production is still on 3.9.
- Use the `Makefile` targets (such as `make install`) instead of invoking `uv` directly unless you are updating tooling.

## Build, Test, and Development Commands

Dependencies are defined in `pyproject.toml`, but installation and local workflows are driven through the `Makefile`. Prefer `make` targets over ad‑hoc commands.

- `make install` – create a virtual environment (if applicable) and install all dependencies from `pyproject.toml`.
- `make dev` – start the local development server / agent runner.
- `make test` – run the full automated test suite (typically `pytest`).
- `make lint` / `make format` – run linting and formatting tools configured in `pyproject.toml`.
- Always run tests and related validations through `uv`-backed targets (for example `uv run pytest` or `uv run my_validation_tool`) rather than invoking the frameworks directly.

Example `Makefile` wiring `uv` to Python 3.13:

```make
PYTHON_VERSION ?= 3.13

install:
	uv python pin $(PYTHON_VERSION)
	uv sync

dev:
	uv run python -m wealth_hub_agent

test:
	uv run pytest
```

## Coding Style & Naming

- Use 2 spaces for indentation unless an existing file clearly uses another style; match the file you touch.
- Prefer descriptive names: `portfolio_risk_analyzer`, not `pra`.
- Modules and files: `snake_case`; classes: `PascalCase`; functions and variables: `snake_case`.
- Keep functions small and focused; extract helpers instead of adding complex branching.

## Testing Guidelines

- Place tests under `tests/` mirroring the source path (for example, `src/agents/portfolio/` → `tests/agents/test_portfolio.py`).
- Name tests clearly and behaviorally (for example, `test_calculates_risk_score_for_mixed_assets`).
- Run `make test` before submitting changes; add tests for all new behavior and bug fixes.

## Commits & Pull Requests

- Write concise, imperative commit messages (for example, `Add portfolio risk constraints`, `Fix cash balance rounding`).
- Keep pull requests focused on a single logical change.
- In PR descriptions, include: purpose, implementation notes, testing performed (commands), and any relevant screenshots or logs.
- Reference related issues (for example, `Closes #123`) when applicable.

## AWS Deployment Notes

- The project is intended to run on AWS (for example, ECS, Lambda, or EC2 behind an ALB). Keep configuration environment‑driven using variables, not hard‑coded secrets.
- Treat `main` (or the primary release branch) as deployable at all times; ensure tests pass locally (`make test`) before merging.
- Avoid committing AWS credentials or secrets; use AWS IAM roles, SSM Parameter Store, or Secrets Manager instead.
- When adding new services or integrations, document required AWS resources and environment variables in the relevant `config/` files or README section.
