# Legal Multimodal GraphRAG System

A legal document intelligence platform that converts source files into a traceable structured representation, retrieval-ready chunks, and a provenance-preserving legal knowledge graph.

---

## Quick Start

### 1. Install dependencies

```bash
pip install pydantic pdfminer.six python-docx beautifulsoup4 lxml
# Optional for OCR:
pip install pytesseract Pillow
# Tesseract binary also required: https://github.com/UB-Mannheim/tesseract/wiki
```

Or install everything:
```bash
pip install -r requirements.txt
```

### 2. Add your documents

Put your legal documents in the `samples/` folder:
```
samples/
  my_contract.pdf
  my_regulation.docx
  my_law.html
  my_scan.png
```

A sample HTML contract is already provided at `samples/sample_contract.html`.

### 3. Run the pipeline evaluator

```bash
# Run with default settings
python -m src.run_pipeline_eval --input ./samples --output ./reports

# Run with specific options
python -m src.run_pipeline_eval \
  --input ./samples \
  --output ./reports \
  --log-level DEBUG

# Disable features
python -m src.run_pipeline_eval --input ./samples --no-graph --no-smoke-test

# Enable AI-assisted repair (requires OpenAI/Anthropic API — not yet wired)
python -m src.run_pipeline_eval --input ./samples --enable-ai-repair
```

### 4. Check the reports

```
reports/
  eval_report_<run_id>.json    ← machine-readable evaluation report
  eval_report_<run_id>.md      ← human-readable Markdown report
  logs/
    trace_<id>_orchestrator.jsonl   ← structured pipeline logs
```

---

## Supported Input Formats

| Format | Extension | Extraction Method |
|---|---|---|
| Text PDF | `.pdf` | pdfminer (local-first) |
| Word Document | `.docx`, `.doc` | python-docx |
| HTML | `.html`, `.htm` | beautifulsoup4 |
| Image / Scanned page | `.png`, `.jpg`, `.tiff`, etc. | pytesseract (OCR) |

---

## Pipeline Stages

| Stage | What it does |
|---|---|
| 1. input_loading | Validate file, detect type, compute source hash |
| 2. document_profiling | Choose extraction strategy (local / hybrid / scan recovery) |
| 3. extraction | Extract text, tables, images — local-first |
| 4. canonical_structuring | Build CanonicalDocument with provenance |
| 5. cleaning_validation | Remove garbage, flag low-confidence content |
| 6. chunking | Structure-aware legal chunking |
| 7. graph_building | Build GraphSubgraph (nodes + edges) |
| 8. retrieval_smoke_test | Keyword-based retrieval validation |

---

## Project Structure

```
src/
  config.py                  ← PipelineConfig (all thresholds and toggles)
  cli.py                     ← CLI argument parser
  run_pipeline_eval.py       ← Main runner ← START HERE

  schemas/
    document.py              ← CanonicalDocument, Block, Table, Image, Section, Article, Clause
    chunk.py                 ← Chunk, ChunkSet, ChunkingDecision
    graph.py                 ← GraphNode, GraphEdge, GraphSubgraph
    evaluation.py            ← PipelineEvalReport, DocumentEvalResult, StageResult

  pipeline/
    interfaces.py            ← StageContext, StageOutput, timed_run
    stages.py                ← All 8 stage implementations
    orchestrator.py          ← PipelineOrchestrator

  evaluation/
    checks.py                ← Per-stage validation checks
    metrics.py               ← Metric computation
    reports.py               ← JSON + Markdown report writers

  utils/
    logging.py               ← PipelineLogger (structured JSON logs)
    trace.py                 ← trace_id, document_id, source_hash utilities

docs/                        ← Architecture documentation (read before modifying)
samples/                     ← Put your test documents here
reports/                     ← Evaluation reports are written here
```

---

## Design Rules (from docs/)

- **Local-first extraction**: AI assistance only with `--enable-ai-repair`
- **No invented text**: Missing content stays missing — never filled with guesses
- **Tables are first-class**: Never flattened into prose
- **Provenance everywhere**: Every block, chunk, and graph node carries `document_id`, `page_id`, `trace_id`
- **Hallucination prevention**: Low-confidence blocks are flagged, not silently trusted
- **Deterministic output**: Same input → same document_id and structure

---

## Exit Codes

| Code | Meaning |
|---|---|
| 0 | All documents passed |
| 1 | Warnings present, no failures |
| 2 | One or more documents failed |
