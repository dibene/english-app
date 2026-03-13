"""Text comparison engine: diffs expected text against a PronunciationResult."""

import string
from difflib import SequenceMatcher

import cmudict

from core.models.diff import DiffEntry, DiffResult
from core.models.pronunciation import PronunciationResult
from core.models.transcription import PhonemeScore

_CMUDICT: dict[str, list[list[str]]] = cmudict.dict()

# Strip all punctuation except apostrophes so contractions like "it's", "won't",
# "I'll" survive and resolve correctly in CMUdict.
_STRIP_PUNCT = str.maketrans("", "", string.punctuation.replace("'", ""))


def _normalize(text: str) -> list[str]:
    """Lowercase and strip punctuation (preserving apostrophes), returning a list of words."""
    text = text.lower()
    text = text.translate(_STRIP_PUNCT)
    return text.split()


def _get_phonemes(word: str) -> list[str] | None:
    """Return ARPAbet phoneme list for word using cmudict, or None if unknown."""
    pronunciations = _CMUDICT.get(word.lower())
    if not pronunciations:
        return None
    return list(pronunciations[0])


class TextComparisonEngine:
    """Compares expected text against a PronunciationResult word by word.

    Uses difflib.SequenceMatcher to align word sequences and classifies each
    position as ok, missing, inserted, or mispronounced.
    """

    def __init__(self, mispronounced_threshold: float = 0.7) -> None:
        self._threshold = mispronounced_threshold

    def compare(
        self,
        expected_text: str,
        result: PronunciationResult,
    ) -> DiffResult:
        """Compare expected text against a PronunciationResult and return a DiffResult.

        Args:
            expected_text: The sentence the user was supposed to say.
            result: The pronunciation assessment output with word-level data.
                WordResult.phoneme_scores is populated by Azure; None for Deepgram.

        Returns:
            DiffResult with a DiffEntry for every expected or spoken word.
        """
        expected_words = _normalize(expected_text)

        # Build parallel lists: normalised spoken words, confidences, and phoneme scores
        spoken_words: list[str] = []
        confidences: list[float | None] = []
        phoneme_scores_by_index: list[list[PhonemeScore] | None] = []
        for wr in result.words:
            normalised = _normalize(wr.word)
            if not normalised:
                continue
            spoken_words.append(normalised[0])
            confidences.append(wr.confidence)
            phoneme_scores_by_index.append(wr.phoneme_scores)

        entries: list[DiffEntry] = []

        matcher = SequenceMatcher(None, expected_words, spoken_words, autojunk=False)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                for offset, (exp, spk) in enumerate(
                    zip(expected_words[i1:i2], spoken_words[j1:j2])
                ):
                    idx = j1 + offset
                    conf = confidences[idx]
                    ph_scores = phoneme_scores_by_index[idx]
                    if conf is not None and conf < self._threshold:
                        entries.append(
                            DiffEntry(
                                expected_word=exp,
                                spoken_word=spk,
                                status="mispronounced",
                                confidence=conf,
                                expected_phonemes=_get_phonemes(exp),
                                phoneme_scores=ph_scores,
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
                                phoneme_scores=ph_scores,
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
                    idx = j1 + offset
                    entries.append(
                        DiffEntry(
                            expected_word=None,
                            spoken_word=spk,
                            status="inserted",
                            confidence=confidences[idx],
                            phoneme_scores=phoneme_scores_by_index[idx],
                        )
                    )

            elif tag == "replace":
                # Words differ; examine each spoken word individually
                # Pair up as many as possible, then handle leftovers
                exp_slice = expected_words[i1:i2]
                spk_slice = spoken_words[j1:j2]
                paired = min(len(exp_slice), len(spk_slice))

                for k in range(paired):
                    idx = j1 + k
                    conf = confidences[idx]
                    ph_scores = phoneme_scores_by_index[idx]
                    if conf is not None and conf < self._threshold:
                        entries.append(
                            DiffEntry(
                                expected_word=exp_slice[k],
                                spoken_word=spk_slice[k],
                                status="mispronounced",
                                confidence=conf,
                                expected_phonemes=_get_phonemes(exp_slice[k]),
                                phoneme_scores=ph_scores,
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
                                phoneme_scores=ph_scores,
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
                    idx = j1 + paired + offset
                    entries.append(
                        DiffEntry(
                            expected_word=None,
                            spoken_word=spk,
                            status="inserted",
                            confidence=confidences[idx],
                            phoneme_scores=phoneme_scores_by_index[idx],
                        )
                    )

        return DiffResult(entries=entries)
