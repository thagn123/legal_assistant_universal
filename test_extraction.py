"""
test_extraction.py
==================

Script kiem tra toan bo pipeline trich xuat + chunking cua ULKA / LexAI
tren mot file van ban phap luat bat ky (PDF / DOCX / DOC / HTML / IMAGE).

Tinh nang:
    1. Chay day du 8 stage cua PipelineOrchestrator (extractor.py thuan).
    2. NEU PDF la dang scan (khong co text layer) -> bat co --ocr de chay
       OCR fallback: chuyen PDF -> anh -> Tesseract -> tao raw_blocks ->
       day vao pipeline va chay tiep structuring -> chunking.
    3. Ho tro song song 2 thu vien convert PDF -> anh, in bang so sanh hieu
       nang de ban tu chon phuong an toi uu:
          - PyMuPDF (fitz)       -- pure Python, khong can Poppler.
          - pdf2image + Poppler  -- pho bien, can cai poppler-utils.

Cach chay:
    python test_extraction.py                                  # khong OCR
    python test_extraction.py --ocr                            # bat OCR
    python test_extraction.py --ocr --ocr-max-pages 5          # 5 trang
    python test_extraction.py --ocr --ocr-method pymupdf
    python test_extraction.py --ocr --ocr-method pdf2image
    python test_extraction.py --ocr --ocr-lang vie+eng
    python test_extraction.py --ocr --full

Yeu cau cai dat (Windows):
    pip install pdfminer.six python-docx beautifulsoup4 pydantic
    pip install PyMuPDF                # cho phuong an pymupdf
    pip install pdf2image pillow       # cho phuong an pdf2image
    pip install pytesseract
    # Cai them: Tesseract OCR + goi tieng Viet; Poppler cho pdf2image.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from src.config import PipelineConfig
from src.pipeline.orchestrator import PipelineOrchestrator
from src.pipeline.interfaces import StageContext
from src.pipeline.profiler import stage_input_loading, stage_document_profiling
from src.pipeline.extractor import stage_extraction
from src.pipeline.structurer import stage_canonical_structuring
from src.pipeline.cleaner import stage_cleaning_validation
from src.pipeline.chunker import stage_chunking
from src.utils.logging import get_logger
from src.utils import trace as T


LINE = "=" * 88
SUB = "-" * 88


def banner(title):
    print()
    print(LINE)
    print(f"  {title}")
    print(LINE)


def sub(title):
    print()
    print(SUB)
    print(f"  {title}")
    print(SUB)


def shorten(text, limit=400):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + f" ... [+{len(text) - limit} ky tu bi cat]"


def _find_tesseract_exe():
    """Tu dong tim tesseract.exe o cac vi tri pho bien tren Windows."""
    import os
    import shutil
    # 1) Neu da nam trong PATH
    found = shutil.which("tesseract")
    if found:
        return found
    # 2) Cac duong dan cai dat pho bien
    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
        os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return None


# Set 1 lan khi import module: cho ca pytesseract (test_extraction.py)
# va pipeline goc (src/pipeline/extractor.py -> _extract_pdf_ocr) deu thay
_TESSERACT_EXE = _find_tesseract_exe()
if _TESSERACT_EXE:
    import os as _os
    # Them thu muc chua tesseract.exe vao PATH cho subprocess
    _tess_dir = str(Path(_TESSERACT_EXE).parent)
    if _tess_dir not in _os.environ.get("PATH", ""):
        _os.environ["PATH"] = _tess_dir + _os.pathsep + _os.environ.get("PATH", "")
    # Cau hinh pytesseract
    try:
        import pytesseract as _pt
        _pt.pytesseract.tesseract_cmd = _TESSERACT_EXE
    except ImportError:
        pass
    print(f"[INFO] Tesseract found at: {_TESSERACT_EXE}")
else:
    print("[WARN] Tesseract NOT found. Cai dat tu https://github.com/UB-Mannheim/tesseract/wiki")


def _preprocess_image_for_ocr(image):
    """Tang chat luong OCR: chuyen grayscale + adaptive threshold (neu PIL co)."""
    try:
        from PIL import Image, ImageOps, ImageFilter
        img = image.convert("L")  # grayscale
        # Tang do tuong phan nhe (auto-contrast)
        img = ImageOps.autocontrast(img, cutoff=1)
        # Sharpen nhe
        img = img.filter(ImageFilter.SHARPEN)
        return img
    except Exception:
        return image


# Tu dien sua loi OCR pho bien khi tesseract khong co `vie` hoac OCR sai dau
_VN_OCR_FIXES = [
    # Tieu de phap ly chinh
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
    # Tu thuong gap
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
    # Cau truc co ban
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


def _postprocess_vn_ocr(text: str) -> str:
    """Sua cac loi OCR pho bien khi tesseract chua co goi 'vie' chuan."""
    import re as _re
    out = text
    for pat, rep in _VN_OCR_FIXES:
        out = _re.sub(pat, rep, out)
    return out


def _is_fake_article_label(label: str) -> bool:
    """
    Phat hien 'Article gia': khi label la TRICH DAN sang van ban khac
    (vd 'Dieu 47 Nghi dinh 96/2026/ND-CP'), khong phai Dieu cua van ban hien tai.
    """
    import re as _re
    if not label:
        return True
    # Co chua "Nghi dinh", "Luat", "Thong tu", "Quyet dinh" -> trich dan
    citation_keywords = [
        r"Nghị\s*định", r"Luật\s+", r"Thông\s*tư", r"Quyết\s*định",
        r"NĐ-CP", r"TT-BTC", r"QH\d+", r"/202\d/",
    ]
    for kw in citation_keywords:
        if _re.search(kw, label, _re.IGNORECASE):
            return True
    # Co ngoac mo nhung khong dong -> noisy
    if label.count("(") != label.count(")"):
        return True
    return False


def _filter_fake_articles(document) -> int:
    """
    Loc cac article gia khoi document. Tra ve so article bi loc.
    Neu sau khi loc khong con article nao -> reset has_structure() = False
    de chunker chuyen sang semantic fallback.
    """
    if not document or not document.articles:
        return 0
    fake_count = 0
    real_articles = []
    for a in document.articles:
        if _is_fake_article_label(a.label):
            fake_count += 1
        else:
            real_articles.append(a)
    document.articles = real_articles
    return fake_count


def _custom_chunk_document(document, max_tokens=500):
    """
    Tu chunk document khi structurer khong detect cau truc thuc su
    (phu luc, mau, bieu...). Gom cac block lien tiep theo thu tu trang,
    moi chunk ~max_tokens.

    Tra ve ChunkSet object da fill cac Chunk objects co kien thuc.
    """
    from src.schemas.chunk import Chunk, ChunkSet, ChunkingDecision
    from src.utils import trace as T

    chunks = []
    if not document or not document.blocks:
        return ChunkSet(
            document_id=document.document_id if document else "unknown",
            chunks=[],
            total_chunks=0,
            strategy_used="custom_semantic",
            created_at=T.now_iso(),
        )

    # Sap xep block theo page_id roi reading order
    blocks = sorted(
        document.blocks,
        key=lambda b: (b.page_id or "", getattr(b, "reading_order_index", 0))
    )

    chunk_idx = 0
    buffer_blocks = []
    buffer_text = ""
    buffer_pages = set()

    def flush():
        nonlocal chunk_idx, buffer_blocks, buffer_text, buffer_pages
        if not buffer_blocks:
            return
        # Tao title tu block dau neu la heading-like
        first_text = (buffer_blocks[0].clean_text or buffer_blocks[0].raw_text or "")[:80]
        hierarchy = first_text.strip().splitlines()[0] if first_text.strip() else ""

        chunk = Chunk(
            chunk_id=T.make_chunk_id(document.document_id, chunk_idx),
            document_id=document.document_id,
            chunk_type="text",
            content_format="markdown",
            content=buffer_text.strip(),
            structure_path=[hierarchy] if hierarchy else [],
            page_refs=sorted(buffer_pages),
            block_refs=[b.block_id for b in buffer_blocks],
            token_estimate=len(buffer_text) // 4,
            confidence=sum(b.confidence.overall for b in buffer_blocks) / len(buffer_blocks),
            degraded=False,
            jurisdiction=document.metadata.jurisdiction,
            version_label=document.metadata.version_label or "",
            document_type=document.metadata.document_type,
            language=document.profile.languages[0] if document.profile.languages else "vi",
            hierarchy_path=hierarchy,
        )
        chunks.append(chunk)
        chunk_idx += 1
        buffer_blocks = []
        buffer_text = ""
        buffer_pages = set()

    for b in blocks:
        text = (b.clean_text or b.raw_text or "").strip()
        if not text:
            continue
        # Neu them block nay vuot qua max_tokens -> flush
        projected = (len(buffer_text) + len(text) + 2) // 4
        if buffer_blocks and projected > max_tokens:
            flush()
        buffer_blocks.append(b)
        buffer_text += ("\n\n" if buffer_text else "") + text
        if b.page_id:
            buffer_pages.add(b.page_id)

    flush()

    decision = ChunkingDecision(
        document_id=document.document_id,
        strategy="custom_semantic",
        fallback_strategy="conservative_fallback",
        decision_confidence=0.85,
        reason_codes=["custom_chunker_from_test_extraction"],
        created_at=T.now_iso(),
    )

    return ChunkSet(
        document_id=document.document_id,
        chunks=chunks,
        chunking_decision=decision,
        total_chunks=len(chunks),
        degraded_chunks=0,
        strategy_used="custom_semantic",
        created_at=T.now_iso(),
    )


def _ocr_image(image, lang):
    """OCR voi cau hinh toi uu cho van ban phap ly tieng Viet."""
    import pytesseract
    if _TESSERACT_EXE:
        pytesseract.pytesseract.tesseract_cmd = _TESSERACT_EXE
    img = _preprocess_image_for_ocr(image)
    # --oem 1 = LSTM engine; --psm 6 = treat as a single uniform block of text
    # Phu hop voi van ban phap luat 1 cot, nhieu doan.
    config = "--oem 1 --psm 6"
    text = pytesseract.image_to_string(img, lang=lang, config=config)
    return _postprocess_vn_ocr(text)


def _make_blocks_from_pages(page_texts, source):
    """
    Tach text/trang thanh raw_blocks 'thong minh':
    - Tach theo dong trong (paragraph) la chinh
    - Neu mot dong la HEADING phap ly (Dieu/Khoan/Chuong/Muc/Phan/Diem) thi
      tach rieng block - giup structurer nhan dien duoc cau truc.
    - Cac dong nho le duoc gop voi paragraph ke truoc neu khong phai heading.
    """
    import re as _re

    blocks = []
    el_idx = 0

    # Pattern nhan dien heading phap ly o dau dong (sau khi da postprocess dau)
    heading_re = _re.compile(
        r"^\s*(?:Điều|Khoản|Chương|Mục|Phần|Điểm)\s+[\w\dIVXLCDM]+",
        _re.IGNORECASE | _re.UNICODE,
    )
    # Pattern cho list marker "1.", "a)", "(1)", v.v.
    list_marker_re = _re.compile(r"^\s*(?:\d+[\.\)]|[a-zA-Z][\.\)]|\(\d+\))\s+\S")

    for page_num, page_text in enumerate(page_texts, start=1):
        if not page_text:
            continue

        # Tach theo dong trong truoc
        paragraphs = [p.strip() for p in page_text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [page_text]

        for para in paragraphs:
            lines = [ln.strip() for ln in para.splitlines() if ln.strip()]
            if not lines:
                continue

            # Duyet tung dong: heading -> block rieng;
            # con lai gom thanh 1 block ngam buffer.
            buffer = []

            def flush():
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
                if heading_re.match(line) or list_marker_re.match(line):
                    # Flush buffer, them line nhu block heading
                    flush()
                    blocks.append({
                        "page_index": page_num,
                        "element_index": el_idx,
                        "raw_text": line,
                        "source": source,
                    })
                    el_idx += 1
                else:
                    buffer.append(line)
            flush()

    return blocks


def ocr_via_pymupdf(path, lang, dpi, max_pages):
    stats = {
        "method": "pymupdf", "available": False, "convert_seconds": 0.0,
        "ocr_seconds": 0.0, "pages_processed": 0, "total_chars": 0,
        "blocks_created": 0, "error": "",
    }
    try:
        import fitz
    except ImportError as exc:
        stats["error"] = f"PyMuPDF not installed: {exc}. Run: pip install PyMuPDF"
        return None, stats
    try:
        from PIL import Image
    except ImportError as exc:
        stats["error"] = f"Pillow not installed: {exc}"
        return None, stats

    stats["available"] = True
    page_texts = []
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)

    doc = fitz.open(str(path))
    page_limit = doc.page_count if max_pages <= 0 else min(max_pages, doc.page_count)
    t_convert = 0.0
    t_ocr = 0.0
    for i in range(page_limit):
        t0 = time.perf_counter()
        page = doc.load_page(i)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        t_convert += time.perf_counter() - t0
        t1 = time.perf_counter()
        text = _ocr_image(img, lang=lang)
        t_ocr += time.perf_counter() - t1
        page_texts.append(text)
    doc.close()

    blocks = _make_blocks_from_pages(page_texts, source="pymupdf+tesseract")
    stats["convert_seconds"] = round(t_convert, 3)
    stats["ocr_seconds"] = round(t_ocr, 3)
    stats["pages_processed"] = page_limit
    stats["total_chars"] = sum(len(t) for t in page_texts)
    stats["blocks_created"] = len(blocks)
    return blocks, stats


def ocr_via_pdf2image(path, lang, dpi, max_pages):
    stats = {
        "method": "pdf2image", "available": False, "convert_seconds": 0.0,
        "ocr_seconds": 0.0, "pages_processed": 0, "total_chars": 0,
        "blocks_created": 0, "error": "",
    }
    try:
        from pdf2image import convert_from_path
    except ImportError as exc:
        stats["error"] = f"pdf2image not installed: {exc}"
        return None, stats

    stats["available"] = True
    last_page = None if max_pages <= 0 else max_pages

    t0 = time.perf_counter()
    try:
        images = convert_from_path(str(path), dpi=dpi, first_page=1, last_page=last_page)
    except Exception as exc:
        stats["error"] = f"pdf2image convert failed: {exc} (can cai Poppler)"
        return None, stats
    stats["convert_seconds"] = round(time.perf_counter() - t0, 3)

    page_texts = []
    t_ocr = 0.0
    for img in images:
        t1 = time.perf_counter()
        page_texts.append(_ocr_image(img, lang=lang))
        t_ocr += time.perf_counter() - t1

    blocks = _make_blocks_from_pages(page_texts, source="pdf2image+tesseract")
    stats["ocr_seconds"] = round(t_ocr, 3)
    stats["pages_processed"] = len(images)
    stats["total_chars"] = sum(len(t) for t in page_texts)
    stats["blocks_created"] = len(blocks)
    return blocks, stats


def run_ocr_methods(path, methods, lang, dpi, max_pages):
    results = []
    if "pymupdf" in methods:
        banner("OCR - Phuong an A: PyMuPDF (fitz)")
        b, s = ocr_via_pymupdf(path, lang=lang, dpi=dpi, max_pages=max_pages)
        print(f"  available        : {s['available']}")
        print(f"  pages_processed  : {s['pages_processed']}")
        print(f"  convert_seconds  : {s['convert_seconds']}")
        print(f"  ocr_seconds      : {s['ocr_seconds']}")
        print(f"  total_chars      : {s['total_chars']}")
        print(f"  blocks_created   : {s['blocks_created']}")
        if s["error"]:
            print(f"  ! error          : {s['error']}")
        results.append((b, s))

    if "pdf2image" in methods:
        banner("OCR - Phuong an B: pdf2image + Poppler")
        b, s = ocr_via_pdf2image(path, lang=lang, dpi=dpi, max_pages=max_pages)
        print(f"  available        : {s['available']}")
        print(f"  pages_processed  : {s['pages_processed']}")
        print(f"  convert_seconds  : {s['convert_seconds']}")
        print(f"  ocr_seconds      : {s['ocr_seconds']}")
        print(f"  total_chars      : {s['total_chars']}")
        print(f"  blocks_created   : {s['blocks_created']}")
        if s["error"]:
            print(f"  ! error          : {s['error']}")
        results.append((b, s))

    banner("BANG SO SANH HIEU NANG OCR")
    print(f"  {'method':<12} {'pages':>6} {'convert(s)':>11} {'ocr(s)':>9} "
          f"{'total(s)':>9} {'chars':>8} {'blocks':>7}")
    print("  " + "-" * 70)
    for _, s in results:
        if not s["available"]:
            print(f"  {s['method']:<12} {'-':>6} {'-':>11} {'-':>9} "
                  f"{'-':>9} {'-':>8} {'-':>7}  (khong kha dung)")
            continue
        total = s["convert_seconds"] + s["ocr_seconds"]
        print(f"  {s['method']:<12} {s['pages_processed']:>6} "
              f"{s['convert_seconds']:>11.3f} {s['ocr_seconds']:>9.3f} "
              f"{total:>9.3f} {s['total_chars']:>8} {s['blocks_created']:>7}")

    usable = [(b, s) for b, s in results if b and s["blocks_created"] > 0]
    if not usable:
        print("\n  ! Khong phuong an OCR nao thanh cong.")
        return None, [s for _, s in results]

    usable.sort(key=lambda x: (-x[1]["total_chars"],
                               x[1]["convert_seconds"] + x[1]["ocr_seconds"]))
    best_blocks, best_stats = usable[0]
    print(f"\n  -> Dung ket qua cua: {best_stats['method']} "
          f"({best_stats['total_chars']} ky tu, "
          f"{best_stats['convert_seconds'] + best_stats['ocr_seconds']:.2f}s)")
    return best_blocks, [s for _, s in results]


def print_profile(profile):
    banner("STAGE 2 - DOCUMENT PROFILE")
    if profile is None:
        print("! Khong co profile")
        return
    rows = [
        ("file_type", profile.file_type),
        ("page_count", profile.page_count),
        ("languages", profile.languages),
        ("is_long_document", profile.is_long_document),
        ("has_tables", profile.has_tables),
        ("table_density", profile.table_density),
        ("image_density", profile.image_density),
        ("scan_quality_score", getattr(profile, "scan_quality_score", "-")),
        ("layout_complexity_score", getattr(profile, "layout_complexity_score", "-")),
        ("extraction_strategy", getattr(profile, "extraction_strategy", "-")),
    ]
    for k, v in rows:
        print(f"  {k:30s}: {v}")
    if getattr(profile, "language_detection", None):
        ld = profile.language_detection
        print(f"  language_detection             : "
              f"language={ld.language}, confidence={ld.confidence:.2f}")


def print_raw_blocks(raw_blocks, raw_tables, raw_images, full, label="STAGE 3 - RAW EXTRACTION OUTPUT"):
    banner(label)
    print(f"  Tong so raw block : {len(raw_blocks)}")
    print(f"  Tong so raw table : {len(raw_tables)}")
    print(f"  Tong so raw image : {len(raw_images)}")
    if not raw_blocks:
        print("  ! Khong trich xuat duoc block nao.")
        return
    show_n = len(raw_blocks) if full else min(40, len(raw_blocks))
    sub(f"In {show_n}/{len(raw_blocks)} raw block dau tien")
    for i, b in enumerate(raw_blocks[:show_n]):
        page = b.get("page_index", "?")
        src = b.get("source", "?")
        text = b.get("raw_text", "")
        limit = 100000 if full else 300
        print(f"\n  [block {i:04d}] page={page} source={src}")
        print(f"    {shorten(text, limit)}")


def print_canonical_document(document):
    banner("STAGE 4 - CANONICAL DOCUMENT STRUCTURE")
    if document is None:
        print("  ! Khong co CanonicalDocument.")
        return
    meta = document.metadata
    print(f"  title           : {meta.title!r}")
    print(f"  document_family : {meta.document_family!r}")
    print(f"  document_type   : {meta.document_type!r}")
    print(f"  jurisdiction    : {meta.jurisdiction!r}")
    print(f"  languages       : {meta.languages}")
    print(f"  issued_date     : {meta.issued_date}")
    print(f"  effective_date  : {meta.effective_date}")
    print(f"  version_label   : {meta.version_label}")
    print()
    print(f"  Tong block       : {document.block_count()}")
    print(f"  Tong section     : {len(document.sections)}")
    print(f"  Tong article     : {len(document.articles)}")
    print(f"  Tong clause      : {len(document.clauses)}")
    print(f"  Tong table       : {document.table_count()}")
    print(f"  Tong image       : {document.image_count()}")
    print(f"  has_structure()  : {document.has_structure()}")
    print(f"  degraded_blocks  : {document.degraded_block_count()}")

    if document.sections:
        sub(f"{len(document.sections)} sections")
        for s in document.sections[:20]:
            print(f"  - {s.section_id} label={s.label!r} title={shorten(s.title or '', 80)!r}")

    if document.articles:
        sub(f"{len(document.articles)} articles (max 20)")
        for a in document.articles[:20]:
            print(f"  - {a.article_id} label={a.label!r} "
                  f"title={shorten(a.title or '', 80)!r} blocks={len(a.block_ids)}")

    if document.clauses:
        sub(f"{len(document.clauses)} clauses (max 10)")
        for c in document.clauses[:10]:
            print(f"  - {c.clause_id} label={c.label!r} "
                  f"parent_article={c.parent_article_id} blocks={len(c.block_ids)}")


def print_chunks(chunk_set, full):
    banner("STAGE 6 - CHUNK SET")
    if chunk_set is None:
        print("  ! Khong co ChunkSet.")
        return
    print(f"  strategy_used    : {chunk_set.strategy_used}")
    print(f"  total_chunks     : {chunk_set.total_chunks}")
    print(f"  text chunks      : {len(chunk_set.text_chunks())}")
    print(f"  table chunks     : {len(chunk_set.table_chunks())}")
    print(f"  degraded chunks  : {chunk_set.degraded_chunks}")
    if chunk_set.chunking_decision:
        d = chunk_set.chunking_decision
        print(f"  decision         : strategy={d.strategy} "
              f"fallback={d.fallback_strategy} confidence={d.decision_confidence}")
        print(f"  routing_signals  : {d.routing_signals}")

    sub("Noi dung tung chunk")
    show_n = len(chunk_set.chunks) if full else min(30, len(chunk_set.chunks))
    for i, c in enumerate(chunk_set.chunks[:show_n]):
        print()
        print(f"  -- CHUNK {i:04d}/{len(chunk_set.chunks)} --")
        print(f"     chunk_id        : {c.chunk_id}")
        print(f"     chunk_type      : {c.chunk_type}")
        print(f"     hierarchy_path  : {c.hierarchy_path!r}")
        print(f"     structure_path  : {c.structure_path}")
        print(f"     page_refs       : {c.page_refs}")
        print(f"     token_estimate  : {c.token_estimate}")
        print(f"     confidence      : {c.confidence:.2f} degraded={c.degraded}")
        print(f"     language        : {c.language}")
        if c.degraded_reasons:
            print(f"     degraded_reasons: {c.degraded_reasons}")
        print(f"     content:")
        limit = 100000 if full else 800
        for line in shorten(c.content, limit).splitlines():
            print(f"        {line}")

    if not full and len(chunk_set.chunks) > show_n:
        print(f"\n  ... (con {len(chunk_set.chunks) - show_n} chunk nua)")


def print_stage_summary(result):
    banner("BANG TOM TAT 8 STAGE")
    print(f"  {'#':>2}  {'stage':<26}  {'status':<10}  {'time(s)':>8}  summary")
    print(f"  {'-'*2}  {'-'*26}  {'-'*10}  {'-'*8}  {'-'*40}")
    for i, s in enumerate(result.stage_results, start=1):
        print(f"  {i:>2}  {s.stage:<26}  {s.status:<10}  "
              f"{s.duration_seconds:>8.3f}  {shorten(s.summary, 60)}")
        for w in s.warnings:
            print(f"      ! warning: {shorten(w, 80)}")
        for e in s.errors:
            print(f"      x error  : {shorten(e, 80)}")
    print()
    print(f"  overall_status : {result.overall_status}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", nargs="?", default=None)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--output", default=None)
    parser.add_argument("--ocr", action="store_true")
    parser.add_argument("--ocr-method", choices=["pymupdf", "pdf2image", "both"], default="both")
    parser.add_argument("--ocr-lang", default="vie+eng")
    parser.add_argument("--ocr-dpi", type=int, default=300)
    parser.add_argument("--ocr-max-pages", type=int, default=0)
    args = parser.parse_args()

    if args.source:
        source_path = Path(args.source).expanduser().resolve()
    else:
        candidates = [
            THIS_DIR / "thong-tu-55-btc-PL1.pdf",
            THIS_DIR / "uploads" / "thong-tu-55-btc-PL1.pdf",
        ]
        source_path = next((p for p in candidates if p.exists()), candidates[0])

    if not source_path.exists():
        print(f"X Khong tim thay file: {source_path}")
        return 2

    output_dir = Path(args.output) if args.output else THIS_DIR / "reports" / "test_extraction"
    output_dir.mkdir(parents=True, exist_ok=True)

    banner("CHAY PIPELINE TRICH XUAT + CHUNK")
    print(f"  Source file : {source_path}")
    print(f"  Output dir  : {output_dir}")
    print(f"  OCR enabled : {args.ocr}")
    if args.ocr:
        print(f"  OCR method  : {args.ocr_method}")
        print(f"  OCR lang    : {args.ocr_lang}")
        print(f"  OCR dpi     : {args.ocr_dpi}")
        print(f"  OCR max pgs : {args.ocr_max_pages or 'all'}")

    cfg = PipelineConfig(
        input_path=source_path.parent,
        output_path=output_dir,
        enable_ocr=True,
        enable_ai_repair=False,
        enable_graph_building=True,
        enable_retrieval_smoke_test=True,
        log_level="WARNING",
        log_to_file=False,
    )
    cfg.ensure_output_dir()

    orchestrator = PipelineOrchestrator(cfg)
    result = orchestrator.run(source_path)
    chunk_set = orchestrator.last_chunk_set

    trace_id = T.new_trace_id()
    logger = get_logger(
        module="test_extraction", trace_id=trace_id,
        document_id="inspect", output_dir=output_dir / "logs", level="WARNING",
    )
    ctx = StageContext(
        trace_id=trace_id, document_id="inspect",
        source_path=source_path, config=cfg, logger=logger,
    )
    stage_input_loading(ctx)
    stage_document_profiling(ctx)
    stage_extraction(ctx)
    stage_canonical_structuring(ctx)

    profile = ctx.get("profile")
    raw_blocks = ctx.get("raw_blocks", [])
    raw_tables = ctx.get("raw_tables", [])
    raw_images = ctx.get("raw_images", [])
    document = ctx.get("document")

    print_profile(profile)
    print_raw_blocks(raw_blocks, raw_tables, raw_images, full=args.full)
    print_canonical_document(document)
    print_chunks(chunk_set, full=args.full)
    print_stage_summary(result)

    # Khi user pass --ocr -> LUON chay OCR nang cao cua test_extraction.py
    # de thay the ket qua kem chat luong cua pipeline goc.
    raw_chars = sum(len(b.get('raw_text', '')) for b in raw_blocks)
    need_ocr = args.ocr  # buoc chay OCR fallback khi user yeu cau

    if need_ocr:
        banner("BAT OCR FALLBACK")
        methods = ["pymupdf", "pdf2image"] if args.ocr_method == "both" else [args.ocr_method]

        ocr_blocks, ocr_stats = run_ocr_methods(
            source_path, methods=methods, lang=args.ocr_lang,
            dpi=args.ocr_dpi, max_pages=args.ocr_max_pages,
        )

        if not ocr_blocks:
            print("\n  X Khong co blocks tu OCR. Dung.")
            return 1

        trace_id2 = T.new_trace_id()
        logger2 = get_logger(
            module="test_extraction_ocr", trace_id=trace_id2,
            document_id="inspect_ocr", output_dir=output_dir / "logs", level="WARNING",
        )
        ctx2 = StageContext(
            trace_id=trace_id2, document_id="inspect_ocr",
            source_path=source_path, config=cfg, logger=logger2,
        )
        stage_input_loading(ctx2)
        stage_document_profiling(ctx2)
        ctx2.put("raw_blocks", ocr_blocks)
        ctx2.put("raw_tables", [])
        ctx2.put("raw_images", [])
        stage_canonical_structuring(ctx2)
        stage_cleaning_validation(ctx2)

        # ----- LOC ARTICLE GIA TRUOC KHI CHUNKING -----
        ocr_document = ctx2.get("document")
        fake_count = _filter_fake_articles(ocr_document)
        if fake_count > 0:
            print(f"\n  i Loc bo {fake_count} 'article gia' (trich dan sang van ban khac)")

        # ----- CHUNKING -----
        # Neu sau khi loc khong con article nao -> tu chunk de tranh fallback ke
        if ocr_document and len(ocr_document.articles) == 0:
            print("  i Khong co article that -> dung CUSTOM CHUNKER (~500 tokens/chunk)")
            ocr_chunk_set = _custom_chunk_document(ocr_document, max_tokens=500)
            ctx2.put("chunk_set", ocr_chunk_set)
        else:
            stage_chunking(ctx2)
            ocr_chunk_set = ctx2.get("chunk_set")

        print_raw_blocks(ocr_blocks, [], [], full=args.full,
                         label="STAGE 3 - RAW BLOCKS SAU OCR")
        print_canonical_document(ocr_document)
        print_chunks(ocr_chunk_set, full=args.full)

        banner("KET QUA OCR FALLBACK")
        print(f"  blocks injected  : {len(ocr_blocks)}")
        if ocr_document:
            print(f"  articles detected: {len(ocr_document.articles)}")
            print(f"  clauses detected : {len(ocr_document.clauses)}")
        if ocr_chunk_set:
            print(f"  chunks produced  : {ocr_chunk_set.total_chunks}")

    banner("KET THUC")
    print(f"  pipeline goc overall_status = {result.overall_status}")
    if not args.ocr and len(raw_blocks) == 0:
        print(f"  ! PDF nay khong co text layer -- thu lai voi co --ocr")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
