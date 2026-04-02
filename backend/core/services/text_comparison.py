"""Text comparison engine: diffs expected text against a PronunciationResult."""

import functools
import string
from difflib import SequenceMatcher
from typing import TYPE_CHECKING

import cmudict
import nltk

if TYPE_CHECKING:
    from g2p_en import G2p as G2pType

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
    "R": "ɹ",
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


# Manual IPA overrides for words where g2p-en produces the wrong result.
# Add entries here only when the neural fallback gets a specific word wrong.
_CUSTOM_WORDS: dict[str, list[str]] = {}

# Vowels that fuse with a following /ɹ/ into a rhotic phoneme (Azure en-US).
_RHOTIC_VOWELS: frozenset[str] = frozenset({"ɛ", "ɑ", "ɔ", "ʊ", "ɪ", "i", "æ"})

# All vowels and diphthongs — used to detect vowel + ɝ sequences where ɝ
# acts as a coda /ɹ/ rather than a standalone syllabic r (e.g. "our" = aʊɹ,
# "fire" = faɪɹ, "layer" = leɪɹ). Contrast with "butter" where ɝ follows a
# consonant and stays standalone.
_ALL_VOWELS: frozenset[str] = frozenset(
    {
        "ɑ",
        "æ",
        "ʌ",
        "ɔ",
        "ɛ",
        "ɝ",
        "ɪ",
        "i",
        "ʊ",
        "u",
        "ə",
        "aʊ",
        "aɪ",
        "eɪ",
        "oʊ",
        "ɔɪ",
    }
)


def _merge_rhotics(phonemes: list[str]) -> list[str]:
    """Merge rhotic clusters into single phonemes matching Azure en-US output.

    Two cases:
    - vowel + ɹ  → vowelɹ   (e.g. ˈɛ + ɹ → ˈɛɹ  for "there", "very")
    - vowel + ɝ  → vowelɹ   (e.g. ˈaʊ + ɝ → ˈaʊɹ for "our", "fire")
      Only when the preceding phoneme is a vowel/diphthong; standalone ɝ
      after a consonant (e.g. "butter") is left untouched.
    """
    out: list[str] = []
    i = 0
    while i < len(phonemes):
        ph = phonemes[i]
        stress = ph[0] if ph and ph[0] in "ˈˌ" else ""
        base = ph[len(stress) :]
        next_ph = phonemes[i + 1] if i + 1 < len(phonemes) else None
        if base in _RHOTIC_VOWELS and next_ph == "ɹ":
            # simple vowel + ɹ  →  vowelɹ
            out.append(stress + base + "ɹ")
            i += 2
        elif base in _ALL_VOWELS and next_ph == "ɝ":
            # vowel/diphthong + ɝ  →  vowelɹ  (trailing rhotic coda)
            out.append(stress + base + "ɹ")
            i += 2
        else:
            out.append(ph)
            i += 1
    return out


@functools.lru_cache(maxsize=1)
def _g2p() -> "G2pType":
    """Lazy singleton for the G2p model. Downloads NLTK data on first call."""
    for pkg, path in [
        ("averaged_perceptron_tagger_eng", "taggers/averaged_perceptron_tagger_eng/"),
        ("cmudict", "corpora/cmudict"),
    ]:
        try:
            nltk.data.find(path)
        except LookupError:
            nltk.download(pkg, quiet=True)
    from g2p_en import G2p

    return G2p()


# Standard English letter-name pronunciations in IPA.
# Used as last-resort fallback for likely acronyms (short all-alpha tokens
# not resolved by CMUdict or the g2p-en neural model).
_LETTER_PHONEMES: dict[str, list[str]] = {
    "a": ["eɪ"],
    "b": ["b", "i"],
    "c": ["s", "i"],
    "d": ["d", "i"],
    "e": ["i"],
    "f": ["ɛ", "f"],
    "g": ["dʒ", "i"],
    "h": ["eɪ", "tʃ"],
    "i": ["aɪ"],
    "j": ["dʒ", "eɪ"],
    "k": ["k", "eɪ"],
    "l": ["ɛ", "l"],
    "m": ["ɛ", "m"],
    "n": ["ɛ", "n"],
    "o": ["oʊ"],
    "p": ["p", "i"],
    "q": ["k", "j", "u"],
    "r": ["ɑ", "r"],
    "s": ["ɛ", "s"],
    "t": ["t", "i"],
    "u": ["j", "u"],
    "v": ["v", "i"],
    "w": ["d", "ʌ", "b", "əl", "j", "u"],
    "x": ["ɛ", "k", "s"],
    "y": ["w", "aɪ"],
    "z": ["z", "i"],
}


def _arpabet_to_ipa(phoneme: str) -> str:
    """Convert an ARPAbet phoneme (with optional stress digit) to IPA.

    Stress digits:  0 = unstressed, 1 = primary (ˈ), 2 = secondary (ˌ).
    The stress marker is prepended to the IPA vowel so that when the phoneme
    list is joined the result reads e.g. /sˈɪstəm/ (marked on the stressed vowel).
    """
    if phoneme and phoneme[-1].isdigit():
        stress, base = phoneme[-1], phoneme[:-1]
    else:
        stress, base = None, phoneme
    # AH0 is the unstressed schwa; AH1/AH2 is the stressed "uh" sound.
    if base == "AH" and stress == "0":
        return "ə"
    ipa = _ARPABET_TO_IPA.get(base, phoneme.lower())
    if stress == "1":
        return "ˈ" + ipa
    if stress == "2":
        return "ˌ" + ipa
    return ipa


def _normalize(text: str) -> list[str]:
    """Lowercase and strip punctuation (preserving apostrophes), returning a list of words."""
    text = text.lower()
    # Normalize curly/smart apostrophes (U+2019, U+02BC) to straight apostrophe so
    # contractions like "it's", "won't", "I'll" resolve correctly in CMUdict.
    text = text.replace("\u2019", "'").replace("\u02bc", "'")
    text = text.translate(_STRIP_PUNCT)
    return text.split()


def _get_phonemes(word: str) -> list[str] | None:
    """Return IPA phoneme list for word using cmudict, g2p-en, or letter-spelling.

    Lookup order:
    1. CMUdict — fast, covers ~130k common English words.
    2. _CUSTOM_WORDS — manual IPA overrides for words g2p-en gets wrong.
    3. g2p-en neural model — handles tech words, compounds, neologisms.
    4. Letter-spelling — last resort for acronyms (URL, HTTP, SQL).
    """
    key = word.lower()
    pronunciations = _CMUDICT.get(key)
    if pronunciations:
        return _merge_rhotics([_arpabet_to_ipa(p) for p in pronunciations[0]])
    # Manual overrides (e.g. words where the neural model is wrong).
    if key in _CUSTOM_WORDS:
        return _CUSTOM_WORDS[key]
    # Neural grapheme-to-phoneme fallback via g2p-en.
    if word.isalpha():
        try:
            arpabet_phones: list[str] = _g2p()(key)
            # g2p-en returns space tokens for whitespace; filter those out.
            return _merge_rhotics([_arpabet_to_ipa(p) for p in arpabet_phones if p != " "])
        except Exception:  # noqa: BLE001 — keep alive if model unavailable
            # Final fallback: spell out letter by letter (acronym mode).
            letter_phones: list[str] = []
            for ch in key:
                phones = _LETTER_PHONEMES.get(ch)
                if phones is None:  # pragma: no cover
                    return None
                letter_phones.extend(phones)
            return letter_phones
    return None


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
