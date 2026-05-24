import sys
from pathlib import Path

# Ensure UTF-8 output
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from src.config import PipelineConfig
from src.pipeline.interfaces import StageContext
from src.pipeline.profiler import stage_input_loading, stage_document_profiling
from src.pipeline.extractor import stage_extraction
from src.pipeline.structurer import stage_canonical_structuring
from src.pipeline.cleaner import stage_cleaning_validation
from src.pipeline.chunker import stage_chunking
from src.utils.logging import get_logger
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r'C:\Users\Admin\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

def main():
    file_path = Path(r"C:\Users\Admin\Downloads\thong-tu-55-btc-PL1.pdf")
    
    if not file_path.exists():
        print(f"Error: File not found at {file_path}")
        return

    config = PipelineConfig(
        input_path=file_path,
        output_path=Path("./test_outputs"),
        enable_ocr=True,
        log_level="ERROR"
    )
    
    logger = get_logger("test_run", "test-trace", "test-doc", config.output_path, "ERROR")
    
    ctx = StageContext(
        trace_id="test-trace",
        document_id="test-doc",
        source_path=file_path,
        config=config,
        logger=logger
    )
    
    print(f"--- Bắt đầu trích xuất file: {file_path.name} ---")
    
    # 1. Input Loading
    stage_input_loading(ctx)
    # 2. Document Profiling
    stage_document_profiling(ctx)
    # 3. Extraction
    print("\n[Đang chạy Extraction...]")
    out_ext = stage_extraction(ctx)
    # ------------------------------------------------------------
    # Clean OCR text in raw blocks and in the canonical document
    # ------------------------------------------------------------
    from src.pipeline.ocr_utils import clean_ocr_text
    # Clean raw_blocks (list of dicts)
    for blk in ctx.get("raw_blocks", []):
        if isinstance(blk, dict) and blk.get("raw_text"):
            blk["raw_text"] = clean_ocr_text(blk["raw_text"])
    # Clean blocks inside the canonical document (if any)
    document = ctx.get("document")
    if document:
        for b in document.blocks:
            if getattr(b, "raw_text", None):
                # Store cleaned version in clean_text attribute for later use
                b.clean_text = clean_ocr_text(b.raw_text)
    # ------------------------------------------------------------
    print(f"Extraction status: {out_ext.status}")
    if out_ext.warnings:
        print(f"Extraction warnings: {out_ext.warnings}")
    if out_ext.errors:
        print(f"Extraction errors: {out_ext.errors}")
    
    raw_blocks = ctx.get("raw_blocks", [])
    print(f"Số lượng raw_blocks: {len(raw_blocks)}")
    
    # 4. Canonical Structuring
    print("\n[Đang chạy Canonical Structuring...]")
    stage_canonical_structuring(ctx)
    
    # 5. Cleaning & Validation
    stage_cleaning_validation(ctx)
    
    document = ctx.get("document")
    if document:
        print(f"Số lượng blocks sau cấu trúc: {document.block_count()}")
        print(f"Số lượng Sections (Phụ lục/Mẫu đơn/Chương): {len(document.sections)}")
        print("\n--- CÁC MẪU ĐƠN / VĂN BẢN PHÁP LÝ PHÂN LOẠI ---")
        forms_found = [s for s in document.sections if s.section_kind == "form"]
        for idx, f in enumerate(forms_found[:20]):
            print(f"Mẫu {idx+1}: Số hiệu: {f.number} | Tên mẫu: {f.title or f.label}")
        if len(forms_found) > 20:
            print("... (còn tiếp) ...")
            
        print("\n--- NỘI DUNG VĂN BẢN ĐƯỢC TRÍCH XUẤT ---")
        for i, block in enumerate(document.blocks[:20]):  # Print first 20 blocks
            text = block.raw_text.strip()
            if len(text) > 200:
                text = text[:200] + "..."
            print(f"Block {i+1}: {text}")
        if document.block_count() > 20:
            print("... (còn tiếp) ...")
            
    # 6. Chunking
    print("\n[Đang chạy Chunking...]")
    stage_chunking(ctx)
    chunk_set = ctx.get("chunk_set")
    
    if chunk_set:
        print(f"Số lượng chunks: {len(chunk_set.chunks)}")
        print("\n--- CÁC CHUNKS ĐƯỢC TẠO RA ---")
        for i, chunk in enumerate(chunk_set.chunks[:10]):  # Print first 10 chunks
            text = chunk.content.strip()
            if len(text) > 300:
                text = text[:300] + "..."
            print(f"Chunk {i+1} [Type: {chunk.chunk_type}]: {text}")
            print("-" * 40)
        if len(chunk_set.chunks) > 10:
            print("... (còn tiếp) ...")

if __name__ == "__main__":
    main()
