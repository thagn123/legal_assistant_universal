# Image Intelligence

## Goal
Define how the system processes scans, diagrams, stamps, signatures, seals, embedded images, and other visual regions that may contain legally relevant evidence or text.

---

## Problem
Legal documents often contain image-only pages, low-quality scans, seals over text, handwritten marks, and diagrams with embedded labels. These regions are not safely recoverable by text parsers alone.

---

## Why It Matters
Image regions may contain operative text, authenticity evidence, or contextual qualifiers. Ignoring them weakens retrieval and may produce false certainty in downstream answers.

---

## Inputs
- Image regions or full-page scans from layout analysis.
- Rendered page images and OCR preprocessing artifacts.
- OCR engine outputs with confidence.
- Visual-region policy thresholds for AI escalation.

---

## Outputs
- `ImageObject`
- extracted text spans where readable
- OCR confidence and cleanup status
- image evidence metadata
- AI-assisted reconstruction output for allowed cases only

---

## Core Ideas
### OCR Rules
- Use local OCR first for scans and image regions that appear text-bearing.
- Preserve raw OCR output before cleanup.
- Cleanup may fix whitespace, common OCR substitutions, and broken line grouping if source evidence supports the repair.

### Image Region Handling
Image regions fall into four classes:
| Class | Handling |
| --- | --- |
| Text-bearing scan | OCR locally, repair selectively. |
| Seal, stamp, signature | Preserve as image evidence and extract text only if legible. |
| Diagram or form | Extract labels and structure if relevant; keep image reference. |
| Decorative or non-legal image | Record presence; deprioritize for retrieval. |

### Scan Cleanup
Allowed mechanical cleanup:
- deskew
- denoise
- contrast normalization
- binarization
- orientation correction
- crop tightening

### AI Assistance Boundary
AI assistance is allowed for:
- low-confidence OCR repair where text remains visually recoverable
- layout reconstruction of complex visual forms
- label extraction from diagrams when local OCR misses visible text

AI assistance is not allowed to:
- invent occluded or unreadable text
- interpret a seal or signature as legal approval without supporting context
- summarize the image into legal conclusions

### Confidence Thresholds
- high confidence: usable as authoritative text
- medium confidence: usable with warning or corroboration
- low confidence: preserve as evidence only; exclude from authoritative quoting unless human-reviewed

---

## Pipeline
1. Receive image region or page scan.
2. Detect orientation and image quality issues.
3. Apply reversible preprocessing.
4. Run local OCR if the region is text-bearing.
5. Score OCR confidence and line grouping stability.
6. If confidence is below threshold and the text is visually present, run AI-assisted repair with strict no-invention rules.
7. Classify the region as textual evidence, visual evidence, mixed evidence, or unreadable evidence.
8. Emit `ImageObject` with extracted text, confidence, and provenance.
9. Link image-derived text to nearby structural units only when alignment is supported.

---

## Rules
### ALWAYS
- Keep the original image or crop reference.
- Preserve raw OCR output and cleaned OCR output separately.
- Distinguish between text-bearing evidence and non-text visual evidence.
- Use confidence thresholds to decide whether image text is answer-eligible.
- Keep page and bounding box anchors for every extracted text span.

### NEVER
- Hallucinate text hidden by blur, occlusion, or low resolution.
- Treat signatures, initials, or stamps as semantic text if they are not legible.
- Merge handwritten annotations into authoritative body text without explicit tagging.
- Drop visual regions that may affect authenticity or interpretation.
- Convert low-confidence image guesses into graph facts.

---

## Decision Logic
```text
if image region is text-bearing and OCR_confidence >= high_threshold:
    accept local OCR
elif image region is text-bearing and OCR_confidence between low and high:
    accept with warning or repair selectively
elif image region is text-bearing and OCR_confidence < low_threshold:
    preserve as unreadable evidence and optionally escalate

if visual complexity is high and text is visibly recoverable:
    allow AI-assisted repair
else:
    keep original evidence without semantic expansion
```

Suggested handling:
- seal or stamp only: preserve image, extract visible text fragments, no semantic inference
- signature block: capture names only if legible; otherwise record signature presence
- diagram with labels: extract labels, preserve spatial relationships if possible

---

## Edge Cases
| Case | Required Behavior |
| --- | --- |
| Faint photocopy of statute page | OCR locally after preprocessing; escalate only if text remains visibly recoverable. |
| Stamp overlays article number | Preserve article context from neighboring text; mark occluded digits uncertain. |
| Handwritten negotiation edits on contract | Store as annotation evidence separate from canonical body text. |
| Embedded company logo near clause heading | Ignore as legal text but keep region metadata. |
| Signature page with typed names and image signatures | Extract typed names, preserve image signatures as evidence objects. |
| Diagram referenced by clause text | Keep image object linked to referring clause and preserve label text. |

---

## Data Model
`ImageObject` minimum fields:
- `image_id`
- `document_id`
- `page_id`
- `bbox`
- `image_class`
- `raw_ocr_text`
- `clean_ocr_text`
- `ocr_confidence`
- `preprocessing_steps[]`
- `ai_repair_used`
- `evidence_status`
- `source_trace`

Optional span fields:
- `text_spans[]`
- `orientation`
- `related_block_ids[]`

---

## Retrieval Impact
Image intelligence prevents silent evidence gaps. It enables retrieval over scanned clauses, image-based annexes, diagram labels, and signature-adjacent language that would otherwise be absent from the index.

---

## GraphRAG Impact
Image-derived content can contribute nodes and edges only when provenance and confidence are strong. Non-text visual evidence remains linkable as supporting context rather than asserted legal facts.

---

## Logging
Always log:
- preprocessing steps
- OCR engine and confidence
- AI escalation reason
- evidence classification
- unreadable-region flags
- answer eligibility status

---

## Validation
- Validate that preprocessing is reversible or non-destructive to audit requirements.
- Validate OCR text against visible spans where possible.
- Validate that low-confidence regions are excluded from authoritative quoting.
- Validate links from image text to structural units.
- Human-review sample low-confidence legal seals, signature blocks, and diagram labels.

---

## Future Improvements
- Better handwriting segmentation.
- Signature block entity extraction with stronger evidence controls.
- Diagram-to-graph spatial relation extraction.
- Visual tamper detection for high-risk documents.
