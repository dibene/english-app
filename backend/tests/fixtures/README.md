# Test Audio Fixtures

Audio files used by `test_deepgram_stt_live.py` for live API tests against Deepgram.

## Generate fixtures

```bash
cd backend
uv run python tests/fixtures/generate_fixtures.py
```

This uses [gTTS](https://gtts.readthedocs.io/) (Google Text-to-Speech, free, no API key) to generate synthetic speech.

## Fixtures

| File | Content | Purpose |
|------|---------|---------|
| `hello_how_are_you.wav` | "Hello, how are you today?" | Full sentence — verify transcript and word-level data |
| `missing_word.wav` | "Hello, how today?" | Fewer words — verify shorter word list vs full sentence |
| `silence.wav` | 2s of silence | Edge case — empty or near-empty transcript |

## Using your own voice

You can drop any WAV recording as `my_voice.wav` in this directory and test it manually:

```python
fixture = FIXTURES_DIR / "my_voice.wav"
result = provider.transcribe(fixture.read_bytes())
print(result.transcript)
```

## Note on format

gTTS produces MP3 content. The files are named `.wav` for consistency but saved with MP3 encoding — Deepgram auto-detects the format from the file content.

Fixtures are **not committed to git** (see `.gitignore`). Regenerate them any time.
