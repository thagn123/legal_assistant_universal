"""
Vietnamese OCR Normalizer
=========================

Shared utilities for OCR-based text extraction with Vietnamese legal documents.

Provides:
- find_tesseract_exe()         : auto-discover tesseract.exe on Windows/Linux/macOS
- configure_pytesseract()      : one-time pytesseract configuration
- preprocess_image_for_ocr(img): grayscale + autocontrast + sharpen
- postprocess_vn_ocr(text)     : fix common Vietnamese OCR errors when `vie`
                                 traineddata is missing or partial
- split_text_into_legal_blocks(): split OCR text by Vietnamese legal headings
                                  (Điều / Khoản / Chương / Mục / Phần / Điểm)
                                  so structurer can detect article hierarchy

These helpers are used by:
- src/pipeline/extractor.py    (PDF OCR fallback, image OCR)
- src/pipeline/profiler.py     (optional: language hints)
- test_extraction.py           (kept as thin wrapper for backward-compat)

All functions degrade gracefully on missing optional dependencies (PIL,
pytesseract) — they return the original input rather than raising.
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Tesseract discovery + configuration
# ---------------------------------------------------------------------------

_TESSERACT_CANDIDATES = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    # Linux / macOS conventional paths (covered by shutil.which("tesseract"))
    "/usr/bin/tesseract",
    "/usr/local/bin/tesseract",
    "/opt/homebrew/bin/tesseract",
]


def find_tesseract_exe() -> Optional[str]:
    """
    Find tesseract executable across platforms.

    Order:
      1. shutil.which("tesseract")  — PATH lookup
      2. Common Windows install paths
      3. %LOCALAPPDATA% per-user install
      4. Conventional Unix paths
    """
    found = shutil.which("tesseract")
    if found:
        return found

    candidates = list(_TESSERACT_CANDIDATES)
    # Per-user Windows install
    localappdata = os.environ.get("LOCALAPPDATA")
    if localappdata:
        candidates.append(
            str(Path(localappdata) / "Programs" / "Tesseract-OCR" / "tesseract.exe")
        )
    userprofile = os.environ.get("USERPROFILE")
    if userprofile:
        candidates.append(
            str(Path(userprofile) / "AppData" / "Local" / "Programs"
                / "Tesseract-OCR" / "tesseract.exe")
        )

    for c in candidates:
        if c and Path(c).exists():
            return c
    return None


_CONFIGURED = False
_TESSERACT_EXE: Optional[str] = None


def configure_pytesseract() -> Optional[str]:
    """
    Configure pytesseract globally (idempotent). Also ensures the directory
    containing tesseract.exe is on PATH so subprocess-based code paths work.

    Returns the resolved tesseract.exe path, or None if not found.
    """
    global _CONFIGURED, _TESSERACT_EXE
    if _CONFIGURED:
        return _TESSERACT_EXE

    _TESSERACT_EXE = find_tesseract_exe()
    if _TESSERACT_EXE:
        # Add to PATH for subprocess-launched tools
        tess_dir = str(Path(_TESSERACT_EXE).parent)
        if tess_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = tess_dir + os.pathsep + os.environ.get("PATH", "")
        try:
            import pytesseract  # type: ignore
            pytesseract.pytesseract.tesseract_cmd = _TESSERACT_EXE
        except ImportError:
            pass

    _CONFIGURED = True
    return _TESSERACT_EXE


# ---------------------------------------------------------------------------
# Image preprocessing
# ---------------------------------------------------------------------------


def preprocess_image_for_ocr(image: Any) -> Any:
    """
    Improve OCR accuracy with simple PIL ops: grayscale, autocontrast, sharpen.
    Returns the original image on failure (degrade gracefully).
    """
    try:
        from PIL import ImageOps, ImageFilter
        img = image.convert("L")  # grayscale
        img = ImageOps.autocontrast(img, cutoff=1)
        img = img.filter(ImageFilter.SHARPEN)
        return img
    except Exception:
        return image


# ---------------------------------------------------------------------------
# Vietnamese OCR text post-processing
# ---------------------------------------------------------------------------

# Common substitutions for when Tesseract `vie` is missing or low-quality.
# Patterns match the diacritic-less or partially-correct OCR output and
# rewrite to the canonical Vietnamese form. Each (pattern, replacement) is
# applied with re.sub in order.
_VN_OCR_FIXES = [
    # Legal hierarchy headings
    (r"\bDi[eéè]u\b", "Điều"),
    (r"\bDieu\b", "Điều"),
    (r"\bDiu\b", "Điều"),
    (r"\bKho[adáà]n\b", "Khoản"),
    (r"\bKhodn\b", "Khoản"),
    (r"\bKhoan\b", "Khoản"),
    (r"\bCh[uưuơo]ng\b", "Chương"),
    (r"\bChuong\b", "Chương"),
    (r"\bM[uưụ]c\b", "Mục"),
    (r"\bPh[aâ]n\b", "Phần"),
    (r"\bPhan\b", "Phần"),
    (r"\bDi[eéè]m\b", "Điểm"),
    (r"\bDiem\b", "Điểm"),
    # Common legal phrasings
    (r"\bPhu l[uưụ]c\b", "Phụ lục"),
    (r"\bPhu luc\b", "Phụ lục"),
    (r"\bM[ãa]u\b", "Mẫu"),
    (r"\bMau\b", "Mẫu"),
    (r"\bNghj dinh\b", "Nghị định"),
    (r"\bNghi dinh\b", "Nghị định"),
    (r"\bTh[oôơ]ng t[uưư]\b", "Thông tư"),
    (r"\bThong tu\b", "Thông tư"),
    (r"\bND-CP\b", "NĐ-CP"),
    (r"\bTT-BTC\b", "TT-BTC"),
    # Standard preamble for VN legal docs
    (r"\bDoc lap\b", "Độc lập"),
    (r"\bDéc lap\b", "Độc lập"),
    (r"\bTy do\b", "Tự do"),
    (r"\bHanh phuc\b", "Hạnh phúc"),
    (r"\bHanh phic\b", "Hạnh phúc"),
    (r"\bC[oôơ]ng h[oô]a\b", "Cộng hòa"),
    (r"\bCONG HOA\b", "CỘNG HÒA"),
    (r"\bXA HOI\b", "XÃ HỘI"),
    (r"\bCHU NGHIA VIET NAM\b", "CHỦ NGHĨA VIỆT NAM"),
]


def postprocess_vn_ocr(text: str) -> str:
    """
    Apply common Vietnamese-OCR fixes.
    Idempotent: applying multiple times produces the same result.
    """
    if not text:
        return text
    out = text
    for pat, rep in _VN_OCR_FIXES:
        out = re.sub(pat, rep, out)
    return out


# ---------------------------------------------------------------------------
# Smart block splitting for OCR pages
# ---------------------------------------------------------------------------


# Pattern: heading lines that should become standalone blocks so structurer
# can detect them as Article / Clause / Chapter / Section / Part / Point.
_HEADING_RE = re.compile(
    r"^\s*(?:Điều|Khoản|Chương|Mục|Phần|Điểm)\s+[\w\dIVXLCDM]+",
    re.IGNORECASE | re.UNICODE,
)

# Numbered list markers ("1.", "a)", "(1)", "i.") that often start a new
# clause/sub-clause and benefit from being a separate block.
_LIST_MARKER_RE = re.compile(
    r"^\s*(?:\d+[\.\)]|[a-zA-Z][\.\)]|\(\d+\))\s+\S"
)


def split_text_into_legal_blocks(
    page_texts: List[str], source: str = "ocr"
) -> List[Dict[str, Any]]:
    """
    Convert a list of (per-page) OCR text strings into raw_blocks suitable for
    the canonical_structuring stage.

    Rules:
      - Paragraph boundaries (blank line) split blocks.
      - Lines that look like legal headings or numbered list markers become
        standalone blocks so structurer can match them.
      - Remaining lines are joined back into prose paragraphs to preserve
        sentence flow.

    Each block has the shape expected by src/pipeline/structurer.py:
        {
          "page_index": int,
          "element_index": int,
          "raw_text": str,
          "source": str,
        }
    """
    blocks: List[Dict[str, Any]] = []
    el_idx = 0

    for page_num, page_text in enumerate(page_texts, start=1):
        if not page_text:
            continue

        paragraphs = [p.strip() for p in page_text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [page_text]

        for para in paragraphs:
            lines = [ln.strip() for ln in para.splitlines() if ln.strip()]
            if not lines:
                continue

            buffer: List[str] = []

            def _flush() -> None:
                nonlocal el_idx, buffer
                if buffer:
                    blocks.append({
                        "page_index": page_num,
                        "element_index": el_idx,
                        "raw_text": " ".join(buffer).strip(),
                        "source": source,
                    })
                    el_idx += 1
                    buffer = []

            for line in lines:
                if _HEADING_RE.match(line) or _LIST_MARKER_RE.match(line):
                    _flush()
                    blocks.append({
                        "page_index": page_num,
                        "element_index": el_idx,
                        "raw_text": line,
                        "source": source,
                    })
                    el_idx += 1
                else:
                    buffer.append(line)
            _flush()

    return blocks
