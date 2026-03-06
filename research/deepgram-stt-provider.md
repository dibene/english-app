# Research: Deepgram STT Provider (F-001)

## Why Research Was Needed

Deepgram is an external Speech-to-Text API not yet used in this codebase. We need to understand the Python SDK, authentication, response format, and error handling to properly implement the SpeechToTextProvider interface and map Deepgram's response to our TranscriptionResult model.

---

## Options Considered

### Option 1: Official Deepgram Python SDK
**Pros:**
- Official library maintained by Deepgram
- Handles authentication, retries, and error handling
- Type hints and modern Python support
- Works with bytes/file objects directly
- Response is well-structured JSON with word-level data

**Cons:**
- Additional dependency (~200KB package)
- Abstracts HTTP layer (less control for custom retry logic)

### Option 2: Direct HTTP API calls (requests/httpx)
**Pros:**
- No additional STT-specific dependency
- Full control over request/response handling
- Could use existing httpx in project

**Cons:**
- Must manually handle authentication headers
- Must manually parse response JSON and handle schema changes
- No built-in retry or rate limiting logic
- More code to maintain

### Option 3: Whisper-compatible local models (faster-whisper)
**Pros:**
- No API key required
- No external API calls (privacy, latency, cost)
- Works offline

**Cons:**
- Deferred to post-MVP (D-001 in features.md)
- Requires local model download and GPU/CPU resources
- Out of scope for F-001

---

## Recommended Approach

**Use the official Deepgram Python SDK (Option 1).**

**Rationale:**
- This is the P0 implementation; optimization can come later
- Official SDK reduces implementation risk and maintenance burden
- SDK handles authentication, retries, and response parsing
- Direct mapping from Deepgram's word-level response to our TranscriptionResult model
- The interface abstraction means we can swap providers later (including local models)

---

## Implementation Details

### Installation
```bash
uv add deepgram-sdk
```

### Authentication
- API key provided via environment variable: `DEEPGRAM_API_KEY`
- DeepgramClient() auto-reads from env if not passed explicitly
- Example:
  ```python
  from deepgram import DeepgramClient
  client = DeepgramClient()  # reads DEEPGRAM_API_KEY from env
  ```

### Transcription Method
For in-memory audio bytes (our use case):
```python
response = client.listen.prerecorded.v("1").transcribe_file(
    {"buffer": audio_bytes},
    {
        "model": "nova-3",
        "smart_format": True,  # punctuation and capitalization
    }
)
```

### Response Structure
Deepgram returns a nested JSON structure:
```json
{
  "metadata": {
    "request_id": "...",
    "duration": 25.933313,
    "channels": 1
  },
  "results": {
    "channels": [{
      "alternatives": [{
        "transcript": "full transcript here",
        "confidence": 0.99902344,
        "words": [
          {
            "word": "yeah",
            "start": 0.08,
            "end": 0.32,
            "confidence": 0.9975586,
            "punctuated_word": "Yeah."
          },
          ...
        ]
      }]
    }]
  }
}
```

**Mapping to our models:**
- `transcript`: `results.channels[0].alternatives[0].transcript`
- `words`: iterate over `results.channels[0].alternatives[0].words[]`
  - `word`: use `word` field (or `punctuated_word` if present)
  - `confidence`: `confidence` (0.0-1.0)
  - `start_time`: `start` (seconds, float)
  - `end_time`: `end` (seconds, float)

### Error Handling

**Expected error scenarios:**
1. **Missing/invalid API key**: DeepgramClient will raise exception on init or first request
2. **Network timeout**: SDK raises timeout exception (default 10s can be configured)
3. **Unsupported audio format**: Deepgram returns 400 with error message
4. **Empty audio / no speech detected**: Valid response with empty `words` array
5. **Rate limit / quota exceeded**: Deepgram returns 429 or 402 (payment required)

**Error handling strategy:**
- Let SDK exceptions propagate initially
- Provider implementation should catch SDK-specific exceptions and raise domain-level exceptions (e.g., `TranscriptionError`)
- Domain layer only sees abstract exceptions, not Deepgram-specific ones
- Detailed error context (request_id, error code) logged but not exposed to domain

### Supported Audio Formats
- WAV, MP3, WebM, FLAC, OGG, and others
- Max file size: 2 GB
- For MVP: expect WebM (browser recording) and WAV (test fixtures)

### Rate Limits
- Free tier: up to 100 concurrent requests
- Request timeout: 10 minutes max processing time
- For MVP: single-user, low volume, no concurrency issues expected

---

## Key Risks and Unknowns

### Risk 1: API Key Management
**Mitigation:** Validate `DEEPGRAM_API_KEY` presence at provider initialization. Fail fast with clear error message if missing.

### Risk 2: Deepgram API Changes
**Mitigation:** Pin SDK version in pyproject.toml. Test with mocked responses to isolate from upstream changes. Abstract interface allows provider swap.

### Risk 3: Empty Transcript Handling
**Mitigation:** Treat empty `words` array as valid case (user said nothing or audio was silent). Return TranscriptionResult with empty transcript and empty words list. Domain layer decides if this is an error.

### Risk 4: Confidence Threshold Tuning
**Mitigation:** Deepgram's confidence scores are well-calibrated. For MVP, accept all transcriptions and let the comparison engine and LLM use confidence scores. Post-MVP can add minimum confidence thresholds.

---

## References

- **Deepgram Python SDK:** https://github.com/deepgram/deepgram-python-sdk
- **Pre-recorded Audio Quickstart:** https://developers.deepgram.com/docs/getting-started-with-pre-recorded-audio
- **API Reference (Pre-recorded):** https://developers.deepgram.com/reference/pre-recorded
- **Supported Audio Formats:** https://developers.deepgram.com/docs/supported-audio-formats
- **Models (Nova-3 recommended):** https://developers.deepgram.com/docs/models-languages-overview

---

## Next Steps

1. Human reviews this research document
2. Create plan/deepgram-stt-provider.md with detailed implementation steps
3. Define abstract SpeechToTextProvider interface
4. Implement DeepgramSTTProvider with SDK
5. Unit test with mocked SDK response
