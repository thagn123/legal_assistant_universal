# Modality Routing

## Goal
Define how text, tables, images, scans, and mixed layouts are routed through the extraction system.

## Region Types
| Region Type | Meaning | Default Processing |
| --- | --- | --- |
| `text` | Paragraphs, headings, clauses, lists. | Local text extraction. |
| `table` | Grid or table-like legal data. | Deterministic table parser, then repair if needed. |
| `image` | Signature, stamp, scan crop, diagram, embedded image. | Preserve image evidence; OCR if text-bearing. |
| `mixed` | Interleaved text/table/image or complex layout. | Layout analysis and targeted repair. |

## Table Requirements
The system must:
- detect tables
- preserve row and column semantics
- preserve merged cells where possible
- preserve headers and repeated headers
- export HTML when Markdown cannot preserve topology
- create retrieval-friendly table projection text

Table projection must never replace the canonical table object.

## Image Requirements
The system must support:
- OCR
- scan cleanup
- stamp and signature preservation
- diagram label extraction when visible
- image evidence linking to nearby legal structures

Image-derived text is authoritative only when confidence is sufficient.

## Long Document With Tables
If a long legal document is mostly text but contains sparse tables:
```text
main body -> long_local
table regions -> table-aware extraction
chunking -> structural body chunks + linked table evidence chunks
```

## Legacy DOC Handling
Legacy `.doc` files may lose table topology during text extraction.

Required behavior:
- mark table preservation as degraded when topology cannot be recovered
- recommend conversion to `.docx` for high-fidelity table extraction
- keep extracted text usable for structure and retrieval when possible

