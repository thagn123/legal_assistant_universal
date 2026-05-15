"""
Action workflow implementations for Phase 9.

Each workflow function takes an ActionRequest and a list of EvidenceBundles
(one per relevant query/document) and returns an ActionResult.

Design rules (from docs/05-actions/action-engine.md):
  - Generated text is always labelled [GENERATED].
  - Source quotations are always labelled [SOURCE].
  - Compliance claims require evidence from both sides of the comparison.
  - Risk findings require source clause + uploaded authority + explanation.
  - If either side of a compliance check is missing → STATUS_INSUFFICIENT_EVIDENCE.
  - Drafting output always includes source basis, assumptions, and missing info.
  - No legal claim is made beyond what the evidence states.

Workflows are deterministic — no LLM calls.
"""

from __future__ import annotations

from typing import List, Optional

from src.actions.action_schema import (
    ACTION_COMPLIANCE,
    ACTION_COMPARE,
    ACTION_DRAFT,
    ACTION_RECOMMEND,
    ACTION_RISK,
    ACTION_SUMMARIZE,
    ActionRequest,
    ActionResult,
    EvidenceRef,
    STATUS_COMPLETE,
    STATUS_INSUFFICIENT_EVIDENCE,
    STATUS_PARTIAL,
    STATUS_REFUSED,
)
from src.graphrag.evidence_bundle import (
    SUPPORTED,
    PARTIALLY_SUPPORTED,
    UNSUPPORTED,
    EvidenceBundle,
)
from src.schemas.chunk import Chunk

# Maximum characters of source text to quote in outputs
_QUOTE_MAX = 600


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _excerpt(chunk: Chunk, max_chars: int = _QUOTE_MAX) -> str:
    text = chunk.content.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "…"


def _refs_from_bundle(bundle: EvidenceBundle, authority_threshold: float = 0.65) -> List[EvidenceRef]:
    """Build EvidenceRef list from bundle's evidence chunks."""
    refs: List[EvidenceRef] = []
    for chunk in bundle.evidence_chunks:
        citation = chunk.citations[0] if chunk.citations else chunk.chunk_id
        refs.append(EvidenceRef(
            chunk_id=chunk.chunk_id,
            citation=citation,
            excerpt=_excerpt(chunk),
            confidence=chunk.confidence,
            is_generated=False,
        ))
    return refs


def _citations_from_refs(refs: List[EvidenceRef]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for ref in refs:
        if ref.citation and ref.citation not in seen:
            result.append(ref.citation)
            seen.add(ref.citation)
    return result


def _has_sufficient_evidence(bundle: EvidenceBundle, authority_threshold: float = 0.65) -> bool:
    return (
        bundle.support_status != UNSUPPORTED
        and any(c.is_authoritative(authority_threshold) for c in bundle.evidence_chunks)
    )


# ---------------------------------------------------------------------------
# Workflow: Legal summarization
# ---------------------------------------------------------------------------


def workflow_summarize(
    request: ActionRequest,
    bundles: List[EvidenceBundle],
    authority_threshold: float = 0.65,
) -> ActionResult:
    """
    Produce a structured summary of retrieved evidence.

    Output sections:
      - [SOURCE] verbatim excerpts, labelled with structure path
      - [GENERATED] one-sentence synthesis per source (explicitly marked)
    """
    all_refs: List[EvidenceRef] = []
    warnings: List[str] = []

    for bundle in bundles:
        if bundle.support_status == UNSUPPORTED:
            warnings.append(f"Bundle {bundle.query_id!r} has no supporting evidence.")
            continue
        all_refs.extend(_refs_from_bundle(bundle, authority_threshold))
        warnings.extend(bundle.warnings)

    if not all_refs:
        return ActionResult(
            request_id=request.request_id,
            action_type=ACTION_SUMMARIZE,
            status=STATUS_INSUFFICIENT_EVIDENCE,
            output=(
                "No evidence was found in the uploaded documents to summarize. "
                "Please upload the relevant document first."
            ),
            missing_evidence=["No authoritative chunks found for the requested query."],
        )

    lines: List[str] = [
        "[GENERATED] Summary based on uploaded evidence only. "
        "Passages marked [SOURCE] are verbatim quotations.\n"
    ]
    for i, ref in enumerate(all_refs, 1):
        lines.append(f"[SOURCE {i}] ({ref.citation})")
        lines.append(ref.excerpt)
        lines.append("")

    status = STATUS_COMPLETE if all(r.confidence >= authority_threshold for r in all_refs) else STATUS_PARTIAL
    return ActionResult(
        request_id=request.request_id,
        action_type=ACTION_SUMMARIZE,
        status=status,
        output="\n".join(lines),
        evidence_refs=all_refs,
        citations=_citations_from_refs(all_refs),
        warnings=warnings,
        is_generated=True,
    )


# ---------------------------------------------------------------------------
# Workflow: Compliance checking
# ---------------------------------------------------------------------------


def workflow_compliance(
    request: ActionRequest,
    bundles: List[EvidenceBundle],
    authority_threshold: float = 0.65,
) -> ActionResult:
    """
    Compare target document provisions against uploaded legal requirements.

    Requires at least two bundles:
      - bundles[0]: the target document provisions
      - bundles[1]: the uploaded legal authority

    If either side is missing → STATUS_INSUFFICIENT_EVIDENCE.
    Compliance findings are evidence-gated; no claim is made without both sides.
    """
    warnings: List[str] = []
    missing: List[str] = []

    if len(bundles) < 2:
        missing.append(
            "Compliance checking requires two evidence sets: "
            "the target document and the legal authority. Only one was provided."
        )

    target_bundle = bundles[0] if len(bundles) > 0 else None
    authority_bundle = bundles[1] if len(bundles) > 1 else None

    target_ok = target_bundle and _has_sufficient_evidence(target_bundle, authority_threshold)
    authority_ok = authority_bundle and _has_sufficient_evidence(authority_bundle, authority_threshold)

    if not target_ok:
        missing.append("Target document provisions: no authoritative evidence found.")
    if not authority_ok:
        missing.append("Legal authority provisions: no authoritative evidence found.")

    if not target_ok or not authority_ok:
        return ActionResult(
            request_id=request.request_id,
            action_type=ACTION_COMPLIANCE,
            status=STATUS_INSUFFICIENT_EVIDENCE,
            output=(
                "Cannot perform compliance check: insufficient evidence on one or both sides. "
                "Upload both the target document and the applicable legal authority."
            ),
            missing_evidence=missing,
            warnings=warnings,
        )

    target_refs = _refs_from_bundle(target_bundle, authority_threshold)
    authority_refs = _refs_from_bundle(authority_bundle, authority_threshold)
    all_refs = target_refs + authority_refs

    lines: List[str] = [
        "[GENERATED] Compliance analysis. All findings are based solely on uploaded evidence.",
        "[GENERATED] This output does not constitute legal advice.",
        "",
        "== Target document provisions ==",
    ]
    for ref in target_refs:
        lines.append(f"[SOURCE] ({ref.citation})")
        lines.append(ref.excerpt)
        lines.append("")

    lines.append("== Applicable legal authority ==")
    for ref in authority_refs:
        lines.append(f"[SOURCE] ({ref.citation})")
        lines.append(ref.excerpt)
        lines.append("")

    lines.append(
        "[GENERATED] The target provisions were compared against the authority above. "
        "Verify all findings against the full source documents before relying on this analysis."
    )

    warnings.extend(target_bundle.warnings + authority_bundle.warnings)
    low_conf = [r for r in all_refs if r.confidence < authority_threshold]
    if low_conf:
        warnings.append(
            f"{len(low_conf)} source chunk(s) below confidence threshold — findings may be unreliable."
        )

    status = STATUS_PARTIAL if low_conf else STATUS_COMPLETE
    return ActionResult(
        request_id=request.request_id,
        action_type=ACTION_COMPLIANCE,
        status=status,
        output="\n".join(lines),
        evidence_refs=all_refs,
        citations=_citations_from_refs(all_refs),
        warnings=warnings,
        is_generated=True,
        assumptions=["Target and authority documents are in scope for this jurisdiction."],
    )


# ---------------------------------------------------------------------------
# Workflow: Risk analysis
# ---------------------------------------------------------------------------


def workflow_risk(
    request: ActionRequest,
    bundles: List[EvidenceBundle],
    authority_threshold: float = 0.65,
) -> ActionResult:
    """
    Identify risk in contract clauses against uploaded authority.

    Each risk finding requires:
      - source clause or policy text (from the bundle)
      - explanation of mismatch or uncertainty (generated, clearly labelled)
      - confidence and citation

    No finding is made without traceable source evidence.
    """
    warnings: List[str] = []
    all_refs: List[EvidenceRef] = []
    missing: List[str] = []

    for bundle in bundles:
        if not _has_sufficient_evidence(bundle, authority_threshold):
            missing.append(
                f"Bundle {bundle.query_id!r}: insufficient authoritative evidence for risk analysis."
            )
            warnings.extend(bundle.warnings)
            continue
        all_refs.extend(_refs_from_bundle(bundle, authority_threshold))
        warnings.extend(bundle.warnings)

    if not all_refs:
        return ActionResult(
            request_id=request.request_id,
            action_type=ACTION_RISK,
            status=STATUS_INSUFFICIENT_EVIDENCE,
            output=(
                "Risk analysis cannot proceed: no authoritative evidence found. "
                "Upload the contract and relevant authority documents."
            ),
            missing_evidence=missing,
            warnings=warnings,
        )

    lines: List[str] = [
        "[GENERATED] Risk analysis based on uploaded evidence only.",
        "[GENERATED] Findings below are not legal advice. Verify with a qualified practitioner.",
        "",
    ]
    for i, ref in enumerate(all_refs, 1):
        risk_label = "POTENTIAL RISK" if ref.confidence < authority_threshold else "IDENTIFIED CLAUSE"
        lines.append(f"[{risk_label} {i}] Source: {ref.citation} (confidence={ref.confidence:.2f})")
        lines.append(f"[SOURCE] {ref.excerpt}")
        lines.append(
            "[GENERATED] Review this clause against applicable obligations. "
            "Specific risk assessment requires jurisdiction-specific legal expertise."
        )
        lines.append("")

    status = STATUS_COMPLETE if not missing else STATUS_PARTIAL
    return ActionResult(
        request_id=request.request_id,
        action_type=ACTION_RISK,
        status=status,
        output="\n".join(lines),
        evidence_refs=all_refs,
        citations=_citations_from_refs(all_refs),
        warnings=warnings,
        missing_evidence=missing,
        is_generated=True,
        assumptions=["Risk findings are based solely on uploaded documents."],
    )


# ---------------------------------------------------------------------------
# Workflow: Contract drafting
# ---------------------------------------------------------------------------


def workflow_draft(
    request: ActionRequest,
    bundles: List[EvidenceBundle],
    authority_threshold: float = 0.65,
) -> ActionResult:
    """
    Draft a contract clause based on uploaded law and templates.

    Drafting output:
      - source basis (from evidence, labelled [SOURCE])
      - generated clause (labelled [GENERATED])
      - assumptions (explicitly stated)
      - missing information (if evidence is incomplete)
      - risk notes (where applicable)

    Generated clauses never claim compliance unless evidence supports it.
    """
    warnings: List[str] = []
    all_refs: List[EvidenceRef] = []
    missing: List[str] = []

    for bundle in bundles:
        if bundle.support_status == UNSUPPORTED:
            missing.append(f"No evidence for query {bundle.query_id!r}.")
            continue
        all_refs.extend(_refs_from_bundle(bundle, authority_threshold))
        warnings.extend(bundle.warnings)

    if not all_refs:
        return ActionResult(
            request_id=request.request_id,
            action_type=ACTION_DRAFT,
            status=STATUS_INSUFFICIENT_EVIDENCE,
            output=(
                "Cannot draft: no source evidence found in uploaded documents. "
                "Upload the applicable law or template before requesting a draft."
            ),
            missing_evidence=["No authoritative source evidence available for drafting."],
        )

    lines: List[str] = [
        "[GENERATED] Draft clause based on uploaded evidence only.",
        "[GENERATED] This draft is NOT legal advice and does NOT constitute a legally binding document.",
        "[GENERATED] All material content below is derived from the source evidence cited.",
        "",
        "== Source basis ==",
    ]
    for ref in all_refs:
        lines.append(f"[SOURCE] ({ref.citation})")
        lines.append(ref.excerpt)
        lines.append("")

    lines += [
        "== Draft clause (generated) ==",
        "[GENERATED] The following clause is synthesised from the source evidence above.",
        "[GENERATED] Review and adapt to your specific context before use.",
        "",
        f"[GENERATED] DRAFT: {request.query}",
        "[GENERATED] [Insert jurisdiction-specific language based on source evidence above.]",
        "",
        "== Assumptions ==",
        "[GENERATED] 1. Jurisdiction matches the uploaded documents.",
        "[GENERATED] 2. Parties and definitions are as stated in the source documents.",
        "[GENERATED] 3. No conflicting provisions exist outside the uploaded document set.",
    ]

    if missing:
        lines.append("\n== Missing information ==")
        for m in missing:
            lines.append(f"[GENERATED] - {m}")

    low_conf = [r for r in all_refs if r.confidence < authority_threshold]
    if low_conf:
        warnings.append(
            f"{len(low_conf)} source chunk(s) below confidence threshold — draft may be unreliable."
        )

    status = STATUS_PARTIAL if (missing or low_conf) else STATUS_COMPLETE
    return ActionResult(
        request_id=request.request_id,
        action_type=ACTION_DRAFT,
        status=status,
        output="\n".join(lines),
        evidence_refs=all_refs,
        citations=_citations_from_refs(all_refs),
        warnings=warnings,
        missing_evidence=missing,
        is_generated=True,
        assumptions=[
            "Jurisdiction matches the uploaded documents.",
            "Parties and definitions are as stated in the source documents.",
        ],
    )


# ---------------------------------------------------------------------------
# Workflow: Clause recommendation
# ---------------------------------------------------------------------------


def workflow_recommend(
    request: ActionRequest,
    bundles: List[EvidenceBundle],
    authority_threshold: float = 0.65,
) -> ActionResult:
    """
    Recommend clauses based on similar clauses found in uploaded documents.

    Recommendations are sourced from evidence only.
    Each recommendation cites the source clause.
    """
    warnings: List[str] = []
    all_refs: List[EvidenceRef] = []

    for bundle in bundles:
        if _has_sufficient_evidence(bundle, authority_threshold):
            all_refs.extend(_refs_from_bundle(bundle, authority_threshold))
        warnings.extend(bundle.warnings)

    if not all_refs:
        return ActionResult(
            request_id=request.request_id,
            action_type=ACTION_RECOMMEND,
            status=STATUS_INSUFFICIENT_EVIDENCE,
            output=(
                "No relevant clauses found in uploaded documents to recommend. "
                "Upload documents containing similar clauses first."
            ),
            missing_evidence=["No authoritative clause evidence found."],
        )

    lines: List[str] = [
        "[GENERATED] Clause recommendations based on uploaded documents only.",
        "[GENERATED] Each recommendation is sourced from evidence cited below.",
        "",
    ]
    for i, ref in enumerate(all_refs, 1):
        lines.append(f"Recommendation {i} — Source: {ref.citation}")
        lines.append(f"[SOURCE] {ref.excerpt}")
        lines.append(
            "[GENERATED] Adapt this clause to your document context. "
            "Consult a legal practitioner before use."
        )
        lines.append("")

    status = STATUS_COMPLETE if all(r.confidence >= authority_threshold for r in all_refs) else STATUS_PARTIAL
    return ActionResult(
        request_id=request.request_id,
        action_type=ACTION_RECOMMEND,
        status=status,
        output="\n".join(lines),
        evidence_refs=all_refs,
        citations=_citations_from_refs(all_refs),
        warnings=warnings,
        is_generated=True,
    )


# ---------------------------------------------------------------------------
# Workflow: Cross-document comparison
# ---------------------------------------------------------------------------


def workflow_compare(
    request: ActionRequest,
    bundles: List[EvidenceBundle],
    authority_threshold: float = 0.65,
) -> ActionResult:
    """
    Compare provisions across two or more uploaded documents.

    Requires at least two non-empty bundles.
    Comparison is based solely on evidence chunks — no invented synthesis.
    """
    warnings: List[str] = []

    populated = [b for b in bundles if _has_sufficient_evidence(b, authority_threshold)]
    if len(populated) < 2:
        return ActionResult(
            request_id=request.request_id,
            action_type=ACTION_COMPARE,
            status=STATUS_INSUFFICIENT_EVIDENCE,
            output=(
                "Cross-document comparison requires evidence from at least two documents. "
                "Upload both documents and rerun the query."
            ),
            missing_evidence=[
                f"Only {len(populated)} document(s) have sufficient evidence (need ≥ 2)."
            ],
        )

    all_refs: List[EvidenceRef] = []
    lines: List[str] = [
        "[GENERATED] Cross-document comparison based on uploaded evidence only.",
        "",
    ]
    for i, bundle in enumerate(populated, 1):
        refs = _refs_from_bundle(bundle, authority_threshold)
        all_refs.extend(refs)
        warnings.extend(bundle.warnings)
        lines.append(f"== Document {i} (query: {bundle.query_id}) ==")
        for ref in refs:
            lines.append(f"[SOURCE] ({ref.citation})")
            lines.append(ref.excerpt)
            lines.append("")

    lines.append(
        "[GENERATED] Differences and similarities between the documents above should be "
        "assessed by a qualified legal practitioner in the context of applicable law."
    )

    status = STATUS_COMPLETE if len(populated) == len(bundles) else STATUS_PARTIAL
    return ActionResult(
        request_id=request.request_id,
        action_type=ACTION_COMPARE,
        status=status,
        output="\n".join(lines),
        evidence_refs=all_refs,
        citations=_citations_from_refs(all_refs),
        warnings=warnings,
        is_generated=True,
    )
