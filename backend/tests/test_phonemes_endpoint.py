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
    """Unknown word is omitted from the response (empty dict)."""
    response = client.post("/phonemes", json={"words": ["xyzzy"]})
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
    """Response contains only the words that exist in CMUdict."""
    response = client.post("/phonemes", json={"words": ["hello", "xyzzy"]})
    assert response.status_code == 200
    data = response.json()
    assert "hello" in data["phonemes"]
    assert "xyzzy" not in data["phonemes"]
