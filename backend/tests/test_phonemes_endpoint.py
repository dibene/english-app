"""Tests for POST /phonemes endpoint."""

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_phonemes_known_word() -> None:
    """Known word returns a non-empty IPA phoneme list."""
    response = client.post("/phonemes", json={"words": ["world"]})
    assert response.status_code == 200
    data = response.json()
    assert "world" in data["phonemes"]
    assert len(data["phonemes"]["world"]) > 0


def test_phonemes_unknown_word() -> None:
    """Word with non-alphabetic characters (digits) is omitted from the response."""
    response = client.post("/phonemes", json={"words": ["r2d2"]})
    assert response.status_code == 200
    assert response.json()["phonemes"] == {}


def test_phonemes_empty_list() -> None:
    """Empty words list returns empty phonemes dict."""
    response = client.post("/phonemes", json={"words": []})
    assert response.status_code == 200
    assert response.json()["phonemes"] == {}


def test_phonemes_deduplication() -> None:
    """Duplicate words produce only one entry in the response."""
    response = client.post("/phonemes", json={"words": ["the", "the", "the"]})
    assert response.status_code == 200
    data = response.json()
    assert list(data["phonemes"].keys()).count("the") == 1


def test_phonemes_mixed_known_and_unknown() -> None:
    """Response contains only recognized words; words with digits are omitted."""
    response = client.post("/phonemes", json={"words": ["hello", "r2d2"]})
    assert response.status_code == 200
    data = response.json()
    assert "hello" in data["phonemes"]
    assert "r2d2" not in data["phonemes"]


def test_phonemes_acronym_letter_fallback() -> None:
    """Acronyms not in CMUdict are spelled out letter-by-letter."""
    response = client.post("/phonemes", json={"words": ["apis", "url"]})
    assert response.status_code == 200
    data = response.json()
    assert "apis" in data["phonemes"]
    assert len(data["phonemes"]["apis"]) > 0
    assert "url" in data["phonemes"]
    assert len(data["phonemes"]["url"]) > 0
