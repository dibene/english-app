"""Live tests for AzurePronunciationProvider — make real API calls to Azure.

These tests are skipped automatically unless both conditions are met:
  1. RUN_PRONUNCIATION_LIVE_TESTS=true  (in backend/.env or environment)
  2. AZURE_SPEECH_KEY and AZURE_SPEECH_REGION are set and non-empty

Run manually with:
    RUN_PRONUNCIATION_LIVE_TESTS=true uv run pytest tests/test_azure_pronunciation_live.py -v

Or set RUN_PRONUNCIATION_LIVE_TESTS=true in backend/.env and run:
    uv run pytest tests/test_azure_pronunciation_live.py -v

These tests require:
- Audio fixture files in tests/fixtures/ (generate with generate_fixtures.py)
- Network access to Azure Speech Services
"""

import os
from pathlib import Path

import pytest

from providers.azure_pronunciation import AzurePronunciationProvider

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# ---------------------------------------------------------------------------
# Skip conditions
# ---------------------------------------------------------------------------

_speech_key = os.environ.get("AZURE_SPEECH_KEY", "").strip()
_speech_region = os.environ.get("AZURE_SPEECH_REGION", "").strip()
_run_live = os.environ.get("RUN_PRONUNCIATION_LIVE_TESTS", "false").lower() == "true"

_skip_reason = ""
if not _run_live:
    _skip_reason = "RUN_PRONUNCIATION_LIVE_TESTS is not set to true in backend/.env"
elif not _speech_key:
    _skip_reason = "AZURE_SPEECH_KEY is not set in backend/.env"
elif not _speech_region:
    _skip_reason = "AZURE_SPEECH_REGION is not set in backend/.env"

skip_if_not_configured = pytest.mark.skipif(
    not _run_live or not _speech_key or not _speech_region,
    reason=_skip_reason or "live tests disabled",
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def live_provider() -> AzurePronunciationProvider:
    return AzurePronunciationProvider(key=_speech_key, region=_speech_region)


# ---------------------------------------------------------------------------
# Live tests
# ---------------------------------------------------------------------------


@skip_if_not_configured
def test_live_assess_returns_scores(live_provider: AzurePronunciationProvider) -> None:
    """Full sentence audio should return a PronunciationResult with valid scores."""
    fixture = FIXTURES_DIR / "hello_how_are_you.wav"
    if not fixture.exists():
        pytest.skip(f"Fixture not found: {fixture}. Run tests/fixtures/generate_fixtures.py")

    result = live_provider.assess(fixture.read_bytes(), "hello how are you")

    assert 0.0 <= result.accuracy_score <= 100.0
    assert 0.0 <= result.fluency_score <= 100.0
    assert 0.0 <= result.completeness_score <= 100.0
    assert len(result.words) > 0


@skip_if_not_configured
def test_live_assess_returns_word_detail(live_provider: AzurePronunciationProvider) -> None:
    """Each word should have an accuracy score and error type."""
    fixture = FIXTURES_DIR / "hello_how_are_you.wav"
    if not fixture.exists():
        pytest.skip(f"Fixture not found: {fixture}")

    result = live_provider.assess(fixture.read_bytes(), "hello how are you")

    for word in result.words:
        assert word.word != ""
        assert 0.0 <= word.accuracy_score <= 100.0
        assert word.error_type in ("None", "Mispronunciation", "Omission", "Insertion")


@skip_if_not_configured
def test_live_assess_returns_phoneme_scores(live_provider: AzurePronunciationProvider) -> None:
    """At least one word should have phoneme-level scores."""
    fixture = FIXTURES_DIR / "hello_how_are_you.wav"
    if not fixture.exists():
        pytest.skip(f"Fixture not found: {fixture}")

    result = live_provider.assess(fixture.read_bytes(), "hello how are you")

    words_with_phonemes = [w for w in result.words if w.phoneme_scores]
    assert len(words_with_phonemes) > 0

    for ph in words_with_phonemes[0].phoneme_scores:
        assert ph.phoneme != ""
        assert 0.0 <= ph.score <= 100.0
