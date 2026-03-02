# Read & Improve Backend

AI Pronunciation Feedback MVP - Backend API built with FastAPI.

## Tech Stack

- **Python**: 3.12+
- **Framework**: FastAPI
- **Package Manager**: uv
- **Testing**: pytest + pytest-cov
- **Linting**: black, isort, mypy, pylint
- **Pre-commit**: Automated code quality checks

## Project Structure

```
backend/
├── api/              # FastAPI routes and app setup
├── core/             # Domain layer (Clean Architecture)
│   ├── interfaces/   # Abstract interfaces
│   ├── services/     # Application services / use cases
│   └── models/       # Domain data models
├── providers/        # Concrete implementations (Deepgram, OpenAI, etc.)
└── tests/            # pytest tests
```

## Setup

### Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) package manager

### Install uv (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install Dependencies

```bash
cd backend
uv sync
```

This will:
- Create a virtual environment in `.venv/`
- Install all dependencies and dev dependencies
- Set up the project

## Running the Application

### Start the development server

```bash
uv run uvicorn api.main:app --reload
```

The API will be available at `http://localhost:8000`

### Change the port (if 8000 is in use)

```bash
uv run uvicorn api.main:app --reload --port 8001
```

### API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Testing

### Run all tests

```bash
uv run pytest
```

### Run tests with coverage report

```bash
uv run pytest --cov=. --cov-report=term-missing
```

### Run a specific test file

```bash
uv run pytest tests/test_health.py -v
```

## Code Quality

### Format code with black

```bash
uv run black .
```

### Sort imports with isort

```bash
uv run isort .
```

### Type checking with mypy

```bash
uv run mypy .
```

### Lint with pylint

```bash
uv run pylint api/ core/ tests/
```

### Run all pre-commit hooks manually

```bash
uv run pre-commit run --all-files
```

## Pre-commit Hooks

Pre-commit hooks are automatically installed and will run before each commit to ensure code quality:

- **black**: Code formatting
- **isort**: Import sorting
- **mypy**: Type checking
- **pylint**: Linting
- **trailing-whitespace**: Remove trailing whitespace
- **end-of-file-fixer**: Ensure files end with a newline
- **check-yaml**: Validate YAML files

Hooks run automatically on `git commit`. To skip (not recommended):

```bash
git commit --no-verify
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env` with your actual API keys and configuration.

## Clean Architecture Principles

This project follows Clean Architecture:

- **Domain Layer** (`core/`): Contains business logic, interfaces, and models. **No external dependencies allowed.**
- **Application Layer** (`api/`): FastAPI routes and request/response handling.
- **Infrastructure Layer** (`providers/`): Concrete implementations of interfaces (Deepgram, OpenAI, etc.)

**Rule**: The domain layer (`core/`) must never import from providers or external services.

## Health Check

Test the API is running:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "ok"}
```

## Development Workflow

1. Create a feature branch: `git checkout -b feat/your-feature`
2. Make changes and commit (pre-commit hooks will run automatically)
3. Run tests: `uv run pytest`
4. Push and create a pull request

## Common Issues

### Port 8000 already in use

Change the port when starting the server:
```bash
uv run uvicorn api.main:app --reload --port 8001
```

### Python version mismatch

Ensure Python 3.12+ is installed. Check with:
```bash
python3 --version
```

### uv command not found

Install uv and add to PATH:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
```

## Next Steps

This is the foundation setup. Future features will add:
- Speech-to-text integration (Deepgram)
- LLM-based feedback (OpenAI)
- Pronunciation analysis
- Audio processing
