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

---

## Architecture Decisions

### ADR-001: Azure Cognitive Services for Pronunciation Assessment

**Decision:** Use Azure Cognitive Services Speech SDK (Pronunciation Assessment) for phoneme-level scoring.

**Context:**
The core value of this app is telling users *exactly* which sound they mispronounced, not just that a word was wrong. We evaluated several options:

| Option | Free tier | Phoneme scores | Notes |
|--------|-----------|---------------|-------|
| Deepgram (confidence) | 72 hrs/month | ❌ | Word confidence only, no pronunciation scoring |
| Speechace | 2.5 hrs/month | ✅ | Language-learning oriented, simpler API |
| **Azure Pronunciation Assessment** | **5 hrs/month** | **✅** | Standard + per-phoneme accuracy, fluency, completeness, prosody |

**Why Azure:**
- Largest free tier (5 hrs/month vs 2.5 hrs)
- Returns accuracy score per phoneme, per word, per sentence
- Returns `ErrorType` per word: `None` / `Mispronunciation` / `Omission` / `Insertion`
- Also provides fluency and prosody scores (useful for future features)
- Official Python SDK (`azure-cognitiveservices-speech`)
- The live demo at https://ai.azure.com/explore/aiservices/speech/pronunciationassessment shows exactly what the API returns

**Consequence:**
- Requires `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION` env vars
- `PronunciationAssessmentProvider` interface keeps the domain layer clean — Azure SDK only lives in `providers/`
- Speechace documented as alternative if Azure quota is exceeded

---

### How to get your Azure Speech API key

1. Go to [portal.azure.com](https://portal.azure.com) and sign in (or create a free account)
2. Click **"Create a resource"** → search for **"Speech"** → select **"Speech service"**
3. Fill in:
   - **Subscription:** your subscription (free tier works)
   - **Resource group:** create new, e.g. `english-app-rg`
   - **Region:** pick the closest to you, e.g. `eastus`, `westeurope`
   - **Name:** e.g. `english-app-speech`
   - **Pricing tier:** `Free F0` (5 hours/month)
4. Click **Review + Create** → **Create**
5. Once deployed, go to the resource → **Keys and Endpoint**
6. Copy **KEY 1** and the **Location/Region** value
7. Add to your `.env`:
   ```
   AZURE_SPEECH_KEY=your_key_here
   AZURE_SPEECH_REGION=eastus   # or whatever region you chose
   ```

> **Note:** The F0 free tier gives you 5 hours of audio per month. There is no credit card required to use the free tier, but you need an Azure account.
