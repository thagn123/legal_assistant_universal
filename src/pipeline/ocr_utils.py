# src/pipeline/ocr_utils.py
"""Utility functions for cleaning OCR output.

These helpers are used after Tesseract OCR to improve the quality of extracted text.
"""

import re
import unicodedata
from typing import List


def _remove_control_chars(text: str) -> str:
    """Remove control characters like carriage returns and form feeds."""
    return re.sub(r"[\r\x0c]", "", text)


def _normalize_unicode(text: str) -> str:
    """Normalize Unicode to NFKC (keeps Vietnamese diacritics)."""
    return unicodedata.normalize("NFKC", text)


def merge_hyphenated_lines(text: str) -> str:
    """Join lines that were split by hyphens or line breaks.

    Examples:
        "Mau-\ngiác" -> "Maugiác"
        "điều\n   khoản" -> "điều khoản"
    """
    # Remove hyphen at end of line and join with next line
    text = re.sub(r"-\s*\n\s*", "", text)
    # If a line ends without punctuation and next line starts lowercase, join with a space
    text = re.sub(r"([^\.\?\!])\n\s+([a-zàâäăãåąčćęèéêëėîïíīłńñóôöòøœßśšûüùūýÿźżžč]+)", r"\1 \2", text, flags=re.I)
    return text


def filter_low_confidence_words(words: List[str], confidences: List[int], min_conf: int) -> List[str]:
    """Keep only words whose confidence is >= min_conf.
    ``confidences`` are integer values (0‑100).
    """
    return [w for w, c in zip(words, confidences) if w.strip() and c >= min_conf]


def remove_noise_lines(text: str) -> str:
    """Delete lines that are too short or consist mostly of non‑alphanumeric characters.
    - Lines with fewer than 3 tokens are removed.
    - Lines where >70 % of characters are non‑alphanumeric are removed.
    """
    cleaned = []
    for line in text.splitlines():
        tokens = line.split()
        if len(tokens) < 3:
            continue
        non_alpha_ratio = sum(1 for ch in line if not ch.isalnum()) / max(len(line), 1)
        if non_alpha_ratio > 0.7:
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def clean_ocr_text(raw: str) -> str:
    """Apply a series of cleaning steps to raw OCR output.
    Returns a polished, readable string.
    """
    txt = raw
    txt = _remove_control_chars(txt)
    txt = _normalize_unicode(txt)
    txt = merge_hyphenated_lines(txt)
    txt = remove_noise_lines(txt)
    # Strip extra spaces at line ends/start and drop empty lines
    txt = "\n".join(line.strip() for line in txt.splitlines() if line.strip())
    return txt
