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

# ARPAbet → IPA mapping aligned with Azure Speech SDK en-US IPA output.
_ARPABET_TO_IPA: dict[str, str] = {
    "AA": "ɑ",
    "AE": "æ",
    "AH": "ʌ",
    "AO": "ɔ",
    "AW": "aʊ",
    "AY": "aɪ",
    "EH": "ɛ",
    "ER": "ɝ",
    "EY": "eɪ",
    "IH": "ɪ",
    "IY": "i",
    "OW": "oʊ",
    "OY": "ɔɪ",
    "UH": "ʊ",
    "UW": "u",
    "B": "b",
    "CH": "tʃ",
    "D": "d",
    "DH": "ð",
    "F": "f",
    "G": "ɡ",
    "HH": "h",
    "JH": "dʒ",
    "K": "k",
    "L": "l",
    "M": "m",
    "N": "n",
    "NG": "ŋ",
    "P": "p",
    "R": "r",
    "S": "s",
    "SH": "ʃ",
    "T": "t",
    "TH": "θ",
    "V": "v",
    "W": "w",
    "Y": "j",
    "Z": "z",
    "ZH": "ʒ",
}


def _arpabet_to_ipa(phoneme: str) -> str:
    """Convert an ARPAbet phoneme (with optional stress digit) to IPA."""
    if phoneme and phoneme[-1].isdigit():
        stress, base = phoneme[-1], phoneme[:-1]
    else:
        stress, base = None, phoneme
    # AH0 is the unstressed schwa; AH1/AH2 is the stressed "uh" sound.
    if base == "AH" and stress == "0":
        return "ə"
    return _ARPABET_TO_IPA.get(base, phoneme.lower())


def _normalize(text: str) -> list[str]:
    """Lowercase and strip punctuation (preserving apostrophes), returning a list of words."""
    text = text.lower()
    # Normalize curly/smart apostrophes (U+2019, U+02BC) to straight apostrophe so
    # contractions like "it's", "won't", "I'll" resolve correctly in CMUdict.
    text = text.replace("\u2019", "'").replace("\u02bc", "'")
    text = text.translate(_STRIP_PUNCT)
    return text.split()


def _get_phonemes(word: str) -> list[str] | None:
    """Return IPA phoneme list for word using cmudict, or None if unknown."""
    pronunciations = _CMUDICT.get(word.lower())
    if not pronunciations:
        return None
    return [_arpabet_to_ipa(p) for p in pronunciations[0]]


def get_phonemes_for_words(words: list[str]) -> dict[str, list[str]]:
    """Return IPA phonemes for each word using CMUdict.

    Words are normalised (lowercase, stripped of punctuation) before lookup.
    Words not found in CMUdict are omitted from the result.

    Args:
        words: List of raw words (may be mixed-case or include punctuation).

    Returns:
        Dict mapping each recognised word to its IPA phoneme list.
    """
    result: dict[str, list[str]] = {}
    for word in words:
        normalised_tokens = _normalize(word)
        if not normalised_tokens:
            continue
        token = normalised_tokens[0]
        if token in result:
            continue
        phonemes = _get_phonemes(token)
        if phonemes is not None:
            result[token] = phonemes
    return result


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
