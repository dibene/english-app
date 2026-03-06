"""Live tests for DeepgramSTTProvider — make real API calls to Deepgram.

Run explicitly with:
    uv run pytest -m live -v

These tests require:
- DEEPGRAM_API_KEY set in the environment (or in backend/.env, loaded externally)
- Audio fixture files in tests/fixtures/ (generate with generate_fixtures.py)
- Network access to api.deepgram.com

They are excluded from the default `uv run pytest` run.
"""

import os
from pathlib import Path

import pytest

from providers.deepgram_stt import DeepgramSTTProvider

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def live_provider() -> DeepgramSTTProvider:
    api_key = os.environ.get("DEEPGRAM_API_KEY", "")
    if not api_key:
        pytest.skip("DEEPGRAM_API_KEY not set — skipping live tests")
    return DeepgramSTTProvider(api_key=api_key)


@pytest.mark.live
def test_live_transcribes_full_sentence(live_provider: DeepgramSTTProvider) -> None:
    """Full sentence audio should return a transcript containing the key words."""
    fixture = FIXTURES_DIR / "hello_how_are_you.wav"
    if not fixture.exists():
        pytest.skip(f"Fixture not found: {fixture}. Run tests/fixtures/generate_fixtures.py")

    audio_bytes = fixture.read_bytes()
    result = live_provider.transcribe(audio_bytes)

    assert "hello" in result.transcript.lower()
    assert len(result.words) > 0
    for word in result.words:
        assert 0.0 <= word.confidence <= 1.0
        assert word.start_time is not None
        assert word.end_time is not None
        assert word.start_time < word.end_time


@pytest.mark.live
def test_live_transcribes_shorter_sentence(live_provider: DeepgramSTTProvider) -> None:
    """Shorter sentence (missing words) should return fewer words than the full one."""
    full_fixture = FIXTURES_DIR / "hello_how_are_you.wav"
    short_fixture = FIXTURES_DIR / "missing_word.wav"
    if not full_fixture.exists() or not short_fixture.exists():
        pytest.skip("Fixtures not found. Run tests/fixtures/generate_fixtures.py")

    full_result = live_provider.transcribe(full_fixture.read_bytes())
    short_result = live_provider.transcribe(short_fixture.read_bytes())

    assert len(short_result.words) < len(full_result.words)


@pytest.mark.live
def test_live_silence_returns_empty_or_minimal_transcript(
    live_provider: DeepgramSTTProvider,
) -> None:
    """Silent audio should return an empty or near-empty transcript."""
    fixture = FIXTURES_DIR / "silence.wav"
    if not fixture.exists():
        pytest.skip(f"Fixture not found: {fixture}. Run tests/fixtures/generate_fixtures.py")

    audio_bytes = fixture.read_bytes()
    result = live_provider.transcribe(audio_bytes)

    # Deepgram may return empty transcript or very short noise artifacts
    assert len(result.transcript.strip()) < 10
