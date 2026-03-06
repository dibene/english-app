"""Text comparison engine: diffs expected text against a TranscriptionResult."""

import string
from difflib import SequenceMatcher

import cmudict

from core.models.diff import DiffEntry, DiffResult
from core.models.transcription import TranscriptionResult

_CMUDICT: dict[str, list[list[str]]] = cmudict.dict()


def _normalize(text: str) -> list[str]:
    """Lowercase and strip punctuation, returning a list of words."""
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    return text.split()


def _get_phonemes(word: str) -> list[str] | None:
    """Return ARPAbet phoneme list for word using cmudict, or None if unknown."""
    pronunciations = _CMUDICT.get(word.lower())
    if not pronunciations:
        return None
    return list(pronunciations[0])


class TextComparisonEngine:
    """Compares expected text against a TranscriptionResult word by word.

    Uses difflib.SequenceMatcher to align word sequences and classifies each
    position as ok, missing, inserted, or mispronounced.
    """

    def __init__(self, mispronounced_threshold: float = 0.7) -> None:
        self._threshold = mispronounced_threshold

    def compare(
        self,
        expected_text: str,
        transcription_result: TranscriptionResult,
    ) -> DiffResult:
        """Compare expected text against transcription and return a DiffResult.

        Args:
            expected_text: The sentence the user was supposed to say.
            transcription_result: The STT output with word-level confidence.

        Returns:
            DiffResult with a DiffEntry for every expected or spoken word.
        """
        expected_words = _normalize(expected_text)

        # Build parallel lists: normalised spoken words + their confidence scores
        spoken_words: list[str] = []
        confidences: list[float] = []
        for wr in transcription_result.words:
            normalised = _normalize(wr.word)
            if not normalised:
                continue
            spoken_words.append(normalised[0])
            confidences.append(wr.confidence)

        entries: list[DiffEntry] = []

        matcher = SequenceMatcher(None, expected_words, spoken_words, autojunk=False)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                for offset, (exp, spk) in enumerate(
                    zip(expected_words[i1:i2], spoken_words[j1:j2])
                ):
                    conf = confidences[j1 + offset]
                    if conf < self._threshold:
                        entries.append(
                            DiffEntry(
                                expected_word=exp,
                                spoken_word=spk,
                                status="mispronounced",
                                confidence=conf,
                                expected_phonemes=_get_phonemes(exp),
                            )
                        )
                    else:
                        entries.append(
                            DiffEntry(
                                expected_word=exp,
                                spoken_word=spk,
                                status="ok",
                                confidence=conf,
                                expected_phonemes=_get_phonemes(exp),
                            )
                        )

            elif tag == "delete":
                # Words expected but not spoken
                for exp in expected_words[i1:i2]:
                    entries.append(
                        DiffEntry(
                            expected_word=exp,
                            spoken_word=None,
                            status="missing",
                            confidence=None,
                            expected_phonemes=_get_phonemes(exp),
                        )
                    )

            elif tag == "insert":
                # Words spoken but not expected
                for offset, spk in enumerate(spoken_words[j1:j2]):
                    entries.append(
                        DiffEntry(
                            expected_word=None,
                            spoken_word=spk,
                            status="inserted",
                            confidence=confidences[j1 + offset],
                        )
                    )

            elif tag == "replace":
                # Words differ; examine each spoken word individually
                # Pair up as many as possible, then handle leftovers
                exp_slice = expected_words[i1:i2]
                spk_slice = spoken_words[j1:j2]
                paired = min(len(exp_slice), len(spk_slice))

                for k in range(paired):
                    conf = confidences[j1 + k]
                    if conf < self._threshold:
                        entries.append(
                            DiffEntry(
                                expected_word=exp_slice[k],
                                spoken_word=spk_slice[k],
                                status="mispronounced",
                                confidence=conf,
                                expected_phonemes=_get_phonemes(exp_slice[k]),
                            )
                        )
                    else:
                        # Different word with good confidence -> inserted + missing pair
                        entries.append(
                            DiffEntry(
                                expected_word=exp_slice[k],
                                spoken_word=None,
                                status="missing",
                                confidence=None,
                                expected_phonemes=_get_phonemes(exp_slice[k]),
                            )
                        )
                        entries.append(
                            DiffEntry(
                                expected_word=None,
                                spoken_word=spk_slice[k],
                                status="inserted",
                                confidence=conf,
                            )
                        )

                # Remaining expected words without a spoken counterpart -> missing
                for exp in exp_slice[paired:]:
                    entries.append(
                        DiffEntry(
                            expected_word=exp,
                            spoken_word=None,
                            status="missing",
                            confidence=None,
                            expected_phonemes=_get_phonemes(exp),
                        )
                    )

                # Remaining spoken words without an expected counterpart -> inserted
                for offset, spk in enumerate(spk_slice[paired:]):
                    entries.append(
                        DiffEntry(
                            expected_word=None,
                            spoken_word=spk,
                            status="inserted",
                            confidence=confidences[j1 + paired + offset],
                        )
                    )

        return DiffResult(entries=entries)
