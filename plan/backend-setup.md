# Plan: Backend Project Setup (F-000)

## Goal
Bootstrap the Python backend project with uv, FastAPI skeleton, Clean Architecture folder structure, and a minimal health check endpoint that can be tested.

## Scope
**In scope:**
- Initialize uv project in backend/ directory (pyproject.toml, .python-version)
- Install dependencies: fastapi, uvicorn, pydantic, pydantic-settings, pytest, httpx (for test client), python-dotenv
- Install dev dependencies: black, isort, mypy, pylint, pytest-cov, pre-commit
- Configure pre-commit hooks with black, isort, mypy, pylint
- Create Clean Architecture folder structure: core/interfaces/, core/services/, core/models/, providers/, api/, tests/
- Implement minimal FastAPI app with GET /health endpoint returning { "status": "ok" }
- Write pytest test confirming /health returns 200
- Create backend/.env.example with placeholder keys for future providers
- Configure all dev tools in pyproject.toml (black, isort, mypy, pylint settings)

**Out of scope (this PR):**
- Any domain logic or business services
- External provider implementations (Deepgram, OpenAI)
- Database setup or ORM configuration
- Docker or deployment configuration
- Frontend integration

## Assessment: Research Not Required
Research was skipped because:
- uv is a standard Python package manager with well-documented initialization commands
- FastAPI follows established patterns for minimal app setup
- The folder structure is explicitly defined in the feature spec
- Health check endpoints are standard practice with no architectural decisions needed
- All tools (uv, FastAPI, pytest) are well-documented and commonly used

## Files to Create or Modify
**Create:**
- backend/.python-version - specify Python 3.12
- backend/pyproject.toml - uv will generate, we'll configure dependencies and dev tools
- backend/.pre-commit-config.yaml - pre-commit hooks configuration
- backend/core/interfaces/__init__.py - empty, marks package
- backend/core/services/__init__.py - empty, marks package
- backend/core/models/__init__.py - empty, marks package
- backend/providers/__init__.py - empty, marks package
- backend/api/__init__.py - empty, marks package
- backend/api/main.py - FastAPI app instance and /health endpoint
- backend/tests/__init__.py - empty, marks package
- backend/tests/test_health.py - pytest test for /health endpoint
- backend/.env.example - placeholder environment variables
- backend/README.md - quick start instructions including dev tools usage

**Modify:**
- None (all files are new)

## Interfaces and Data Models
No domain interfaces or models are needed for this feature. This is pure infrastructure setup.

**Health endpoint response model:**
```python
# Simple dict response, no Pydantic model needed yet
{"status": "ok"}
```

## Implementation Steps

### Step 1: Initialize uv project
- Create backend/ directory
- Run `uv init` in backend/ directory
- Set Python version to 3.12 in .python-version
- Verify pyproject.toml is created

### Step 2: Add dependencies
- Run `uv add fastapi uvicorn pydantic pydantic-settings httpx python-dotenv`
- Run `uv add --dev pytest pytest-cov black isort mypy pylint pre-commit`
- Verify dependencies are in pyproject.toml under [project.dependencies] and [tool.uv.dev-dependencies]
- Run `uv sync` to create virtual environment and install packages

### Step 3: Configure dev tools in pyproject.toml
- Add [tool.black] section: line-length = 100, target-version = ['py312']
- Add [tool.isort] section: profile = "black", line_length = 100
- Add [tool.mypy] section: python_version = "3.12", strict = true, ignore_missing_imports = true
- Add [tool.pylint] section: max-line-length = 100, disable = ["C0111", "C0103"]
- Add [tool.pytest.ini_options] section: testpaths = ["tests"], python_files = "test_*.py"
- Add [tool.coverage.run] section: source = ["."], omit = ["tests/*"]

### Step 4: Setup pre-commit hooks
- Create .pre-commit-config.yaml with hooks for:
  - black (code formatting)
  - isort (import sorting)
  - mypy (type checking)
  - pylint (linting)
  - trailing-whitespace, end-of-file-fixer, check-yaml (basic checks)
- Run `uv run pre-commit install` to install git hooks

### Step 5: Create folder structure
- Create all required directories: core/interfaces/, core/services/, core/models/, providers/, api/, tests/
- Add __init__.py to each package directory (Python package markers)

### Step 6: Implement FastAPI app with health endpoint
- Create backend/api/main.py
- Define FastAPI() app instance
- Implement GET /health route handler returning {"status": "ok"}
- Add basic CORS middleware configuration for future frontend integration (localhost:3000)

### Step 7: Write pytest test for health endpoint
- Create backend/tests/test_health.py
- Use httpx TestClient to test GET /health
- Assert response status code is 200
- Assert response body is {"status": "ok"}

### Step 8: Create .env.example
- Create backend/.env.example
- Add placeholder keys: DEEPGRAM_API_KEY, OPENAI_API_KEY, STT_PROVIDER, LLM_PROVIDER
- Add comments explaining each variable

### Step 9: Document setup in README
- Create backend/README.md
- Document: how to install dependencies (uv sync)
- Document: how to run the server (uv run uvicorn api.main:app --reload)
- Document: how to run tests (uv run pytest)
- Document: how to run linting/formatting (uv run black ., uv run mypy ., etc.)
- Document: how to use pre-commit (uv run pre-commit run --all-files)
- Document: default port (8000)

### Step 10: Verify end-to-end
- Run pre-commit on all files: `uv run pre-commit run --all-files`
- Run the test suite: `uv run pytest`
- Run type checking: `uv run mypy .`
- Start the server: `uv run uvicorn api.main:app --reload`
- Manually verify GET http://localhost:8000/health returns {"status": "ok"}

## Test Cases
All test cases must pass before the PR is marked ready for review:

1. **test_health_endpoint_returns_200**
   - Arrange: TestClient with FastAPI app
   - Act: GET /health
   - Assert: status_code == 200

2. **test_health_endpoint_returns_correct_body**
   - Arrange: TestClient with FastAPI app
   - Act: GET /health
   - Assert: response.json() == {"status": "ok"}

3. **test_health_endpoint_with_trailing_slash** (optional but good practice)
   - Arrange: TestClient with FastAPI app
   - Act: GET /health/
   - Assert: status_code in [200, 307] (either OK or redirect)

## High-Level Error/Failure Modes Addressed

### Missing .env file
- Not critical at this stage since no external APIs are called yet
- .env.example documents required variables for future use
- python-dotenv installed but .env not required to start server yet

### Port conflict on default port 8000
- Document in README how to change port: `uvicorn api.main:app --port 8001`
- uvicorn will show clear error message if port is in use

### Python version mismatch
- .python-version file ensures uv uses correct Python version
- Document required Python version (3.12) in README

## Definition of Done
- [ ] backend/ directory exists with initialized uv project
- [ ] pyproject.toml contains all required dependencies and dev dependencies
- [ ] pyproject.toml contains configuration for black, isort, mypy, pylint, pytest
- [ ] .pre-commit-config.yaml is configured with all hooks
- [ ] Pre-commit hooks are installed and run successfully: `uv run pre-commit run --all-files`
- [ ] All folder structure directories exist (core/interfaces/, core/services/, core/models/, providers/, api/, tests/)
- [ ] FastAPI app runs without errors: `uv run uvicorn api.main:app --reload`
- [ ] GET /health returns {"status": "ok"} with status 200
- [ ] All pytest tests pass: `uv run pytest`
- [ ] Type checking passes: `uv run mypy .`
- [ ] Code formatting is correct: `uv run black . --check`
- [ ] Import sorting is correct: `uv run isort . --check`
- [ ] Linting passes: `uv run pylint api/ core/ tests/`
- [ ] backend/.env.example exists with placeholder keys
- [ ] backend/README.md documents setup, run, and dev tool commands
- [ ] No typing errors (all functions have type hints)
- [ ] CORS configured for localhost:3000 (future frontend)

## Notes
- This is a P0 feature - all other backend features depend on this foundation
- Keep it minimal - no domain logic, no external integrations yet
- Follow Clean Architecture: api/ layer is separate from core/
- Use uv throughout (no pip, no manual venv creation)
