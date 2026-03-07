"""Live tests for AzurePronunciationProvider — make real API calls to Azure.

Run explicitly with:
    uv run pytest -m live -v

These tests require:
- AZURE_SPEECH_KEY and AZURE_SPEECH_REGION set in the environment (or in backend/.env)
- Audio fixture files in tests/fixtures/ (generate with generate_fixtures.py)
- Network access to Azure Speech Services

They are excluded from the default `uv run pytest` run.
"""

import os
from pathlib import Path

import pytest

from providers.azure_pronunciation import AzurePronunciationProvider

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def live_provider() -> AzurePronunciationProvider:
    key = os.environ.get("AZURE_SPEECH_KEY", "")
    region = os.environ.get("AZURE_SPEECH_REGION", "")
    if not key:
        pytest.skip("AZURE_SPEECH_KEY not set — skipping live tests")
    if not region:
        pytest.skip("AZURE_SPEECH_REGION not set — skipping live tests")
    return AzurePronunciationProvider(key=key, region=region)


@pytest.mark.live
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


@pytest.mark.live
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


@pytest.mark.live
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
