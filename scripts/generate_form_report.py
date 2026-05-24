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

def main():
    file_path = Path(r"C:\Users\Admin\Downloads\thong-tu-55-btc-PL1.pdf")
    if not file_path.exists():
        file_path = Path("./thong-tu-55-btc-PL1.pdf")
    
    config = PipelineConfig(
        input_path=file_path,
        output_path=Path("./test_outputs"),
        enable_ocr=True,
        log_level="ERROR"
    )
    
    logger = get_logger("report_run", "test-trace", "test-doc", config.output_path, "ERROR")
    
    ctx = StageContext(
        trace_id="test-trace",
        document_id="test-doc",
        source_path=file_path,
        config=config,
        logger=logger
    )
    
    stage_input_loading(ctx)
    stage_document_profiling(ctx)
    stage_extraction(ctx)
    
    # Clean OCR text
    from src.pipeline.ocr_utils import clean_ocr_text
    for blk in ctx.get("raw_blocks", []):
        if isinstance(blk, dict) and blk.get("raw_text"):
            blk["raw_text"] = clean_ocr_text(blk["raw_text"])
            
    stage_canonical_structuring(ctx)
    stage_cleaning_validation(ctx)
    
    document = ctx.get("document")
    if not document:
        print("Error: Could not structure the document.")
        return
        
    forms = [s for s in document.sections if s.section_kind == "form"]
    
    # Generate report content
    report_lines = []
    report_lines.append("# Báo cáo Trích xuất và Phân loại Mẫu Văn bản Pháp lý\n")
    report_lines.append(f"**Tài liệu gốc:** `{file_path.name}`\n")
    report_lines.append(f"**Tổng số mẫu phát hiện:** {len(forms)}\n")
    report_lines.append("| STT | Mã số / Ký hiệu | Tên mẫu văn bản / Quyết định / Đơn từ | Trang |")
    report_lines.append("| --- | --- | --- | --- |")
    
    for idx, f in enumerate(forms):
        title = (f.title or f.label).strip()
        # Clean title if it contains line breaks
        title = title.replace("\n", " ")
        # Truncate title if it's too long
        if len(title) > 150:
            title = title[:147] + "..."
        # Find page index
        pages = ", ".join(str(p.split("_")[-1]) for p in f.page_refs) if f.page_refs else "N/A"
        number = f.number if f.number else "Không có số"
        report_lines.append(f"| {idx+1} | **{number}** | {title} | {pages} |")
        
    # Write report to test_outputs/form_report.md
    out_dir = Path("./test_outputs")
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "form_report.md"
    with open(report_path, "w", encoding="utf-8") as rep_f:
        rep_f.write("\n".join(report_lines))
        
    print(f"Report successfully generated at: {report_path.resolve()}")

if __name__ == "__main__":
    main()
