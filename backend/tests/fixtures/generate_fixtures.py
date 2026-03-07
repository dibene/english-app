"""Generate audio fixture files for live STT tests using gTTS.

Usage:
    cd backend
    uv run python tests/fixtures/generate_fixtures.py

Generates:
    tests/fixtures/hello_how_are_you.wav  — full sentence (PCM 16kHz mono)
    tests/fixtures/missing_word.wav       — sentence with missing words
    tests/fixtures/silence.wav            — 2 seconds of silence

Requires: gTTS (already in dev dependencies), ffmpeg (system), wave (stdlib)
"""

import io
import struct
import subprocess
import wave
from pathlib import Path

from gtts import gTTS  # type: ignore[import]

FIXTURES_DIR = Path(__file__).parent


def text_to_wav(text: str, output_path: Path) -> None:
    """Convert text to speech and save as PCM WAV (16kHz, 16-bit, mono).

    gTTS generates MP3. We pipe it through ffmpeg to produce the PCM WAV
    format expected by the Azure Speech SDK push stream.
    """
    tts = gTTS(text=text, lang="en", slow=False)
    mp3_buffer = io.BytesIO()
    tts.write_to_fp(mp3_buffer)
    mp3_buffer.seek(0)

    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            "pipe:0",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-sample_fmt",
            "s16",
            "-f",
            "wav",
            "pipe:1",
        ],
        input=mp3_buffer.read(),
        capture_output=True,
        check=True,
    )
    output_path.write_bytes(result.stdout)
    print(f"  Created: {output_path} ({output_path.stat().st_size} bytes)")


def create_silence_wav(output_path: Path, duration_seconds: float = 2.0) -> None:
    """Generate a WAV file containing pure silence."""
    sample_rate = 16000
    n_channels = 1
    sampwidth = 2  # 16-bit
    n_frames = int(sample_rate * duration_seconds)

    with wave.open(str(output_path), "w") as wf:
        wf.setnchannels(n_channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{n_frames}h", *([0] * n_frames)))

    print(f"  Created: {output_path} ({output_path.stat().st_size} bytes)")


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    print("Generating audio fixtures...")

    text_to_wav(
        text="Hello, how are you today?",
        output_path=FIXTURES_DIR / "hello_how_are_you.wav",
    )
    text_to_wav(
        text="Hello, how today?",
        output_path=FIXTURES_DIR / "missing_word.wav",
    )
    create_silence_wav(
        output_path=FIXTURES_DIR / "silence.wav",
        duration_seconds=2.0,
    )

    print("\nDone. You can now run: uv run pytest -m live")


if __name__ == "__main__":
    main()
