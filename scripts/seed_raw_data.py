#!/usr/bin/env python3
"""
Seed raw Vietnamese legal documents into the LexAI admin API.

Discovers all .doc / .docx files under raw_data/ and uploads them in
batches via POST /admin/documents/upload, then polls until every job
reaches a terminal state (completed / failed).

Usage:
    python scripts/seed_raw_data.py
    python scripts/seed_raw_data.py --api-url http://localhost:8000 --admin-key lexai-admin-secret
    python scripts/seed_raw_data.py --dry-run          # list files only
    python scripts/seed_raw_data.py --no-wait          # upload and exit immediately

Requirements:
    pip install requests   (already in requirements.txt via httpx/requests)
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# ── Dependency guard ─────────────────────────────────────────────────────────
try:
    import requests
except ImportError:
    print("ERROR: 'requests' is not installed.  Run:  pip install requests")
    sys.exit(1)

# ── Defaults ─────────────────────────────────────────────────────────────────
_DEFAULT_API_URL   = "http://localhost:8000"
_DEFAULT_ADMIN_KEY = os.environ.get("ADMIN_API_KEY", "lexai-admin-secret")
_RAW_DATA_DIR      = Path(__file__).parent.parent / "raw_data"
_POLL_INTERVAL_S   = 5
_MAX_WAIT_S        = 300   # 5 minutes per job batch
_EXTENSIONS        = {".doc", ".docx", ".pdf", ".html"}


# ── File discovery ────────────────────────────────────────────────────────────

def discover_files(root: Path) -> list[Path]:
    found: list[Path] = []
    for ext in _EXTENSIONS:
        found.extend(root.rglob(f"*{ext}"))
    found.sort()
    return found


# ── Upload ────────────────────────────────────────────────────────────────────

def upload_batch(
    files: list[Path],
    api_url: str,
    admin_key: str,
    batch_size: int = 5,
) -> list[str]:
    """Upload files in batches of *batch_size*. Returns list of doc_ids created."""
    doc_ids: list[str] = []
    total = len(files)
    for i in range(0, total, batch_size):
        batch = files[i : i + batch_size]
        print(f"\n[{i + 1}–{min(i + batch_size, total)}/{total}] Uploading batch …")

        file_handles = []
        try:
            for fp in batch:
                fh = open(fp, "rb")  # noqa: WPS515
                file_handles.append(("files", (fp.name, fh, "application/octet-stream")))
                print(f"  + {fp.name}  ({fp.stat().st_size / 1024:.1f} KB)")

            resp = requests.post(
                f"{api_url}/admin/documents/upload",
                headers={"X-Admin-Key": admin_key},
                files=file_handles,
                timeout=120,
            )
        finally:
            for _, (_, fh, _) in file_handles:
                fh.close()

        if resp.status_code not in (200, 201):
            print(f"  ERROR {resp.status_code}: {resp.text[:300]}")
            continue

        data = resp.json()
        # API returns {"documents": [...], "jobs": [...]}
        batch_ids = [d["doc_id"] for d in data.get("documents", [])]
        doc_ids.extend(batch_ids)
        print(f"  Created {len(batch_ids)} document(s): {batch_ids}")

    return doc_ids


# ── Poll jobs ─────────────────────────────────────────────────────────────────

def wait_for_jobs(
    doc_ids: list[str],
    api_url: str,
    admin_key: str,
    max_wait_s: int = _MAX_WAIT_S,
    poll_s: int = _POLL_INTERVAL_S,
) -> dict[str, str]:
    """Poll /admin/jobs until all doc_ids reach terminal status. Returns {doc_id: status}."""
    if not doc_ids:
        return {}
    print(f"\nWaiting for {len(doc_ids)} job(s) to complete (max {max_wait_s}s) …")
    terminal = {"completed", "failed", "error"}
    statuses: dict[str, str] = {d: "pending" for d in doc_ids}
    deadline = time.monotonic() + max_wait_s

    while time.monotonic() < deadline:
        resp = requests.get(
            f"{api_url}/admin/jobs",
            headers={"X-Admin-Key": admin_key},
            params={"limit": 200},
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"  Poll error {resp.status_code}: {resp.text[:200]}")
            time.sleep(poll_s)
            continue

        jobs = resp.json().get("jobs", [])
        for job in jobs:
            doc_id = job.get("doc_id")
            if doc_id in statuses:
                statuses[doc_id] = job.get("status", "unknown")

        pending = [d for d, s in statuses.items() if s not in terminal]
        done = len(statuses) - len(pending)
        print(f"  {done}/{len(statuses)} done — pending: {pending[:5]}")

        if not pending:
            break
        time.sleep(poll_s)
    else:
        print("  WARNING: timeout reached — some jobs may still be running.")

    return statuses


# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary(statuses: dict[str, str]) -> None:
    print("\n" + "═" * 60)
    print("SEED SUMMARY")
    print("═" * 60)
    from collections import Counter
    counts = Counter(statuses.values())
    for status, count in sorted(counts.items()):
        mark = "✓" if status == "completed" else "✗" if status in ("failed", "error") else "?"
        print(f"  {mark}  {status}: {count}")
    failed = [d for d, s in statuses.items() if s in ("failed", "error")]
    if failed:
        print("\nFailed doc_ids:")
        for d in failed:
            print(f"  - {d}")
    print("═" * 60)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed raw Vietnamese legal .doc files into the LexAI admin API."
    )
    parser.add_argument("--api-url",   default=_DEFAULT_API_URL,   help="Backend base URL")
    parser.add_argument("--admin-key", default=_DEFAULT_ADMIN_KEY, help="Admin API key")
    parser.add_argument("--batch-size", type=int, default=3,        help="Files per upload request")
    parser.add_argument("--no-wait",   action="store_true",         help="Upload and exit; skip polling")
    parser.add_argument("--dry-run",   action="store_true",         help="List files only, no upload")
    args = parser.parse_args()

    print("LexAI — Raw Data Seeder")
    print(f"  API:       {args.api_url}")
    print(f"  data dir:  {_RAW_DATA_DIR}")

    files = discover_files(_RAW_DATA_DIR)
    if not files:
        print("No .doc/.docx/.pdf/.html files found in raw_data/")
        sys.exit(0)

    print(f"\nFound {len(files)} file(s):")
    for f in files:
        print(f"  {f.relative_to(_RAW_DATA_DIR.parent)}")

    if args.dry_run:
        print("\n[dry-run] No files uploaded.")
        return

    # Verify API is reachable
    try:
        resp = requests.get(f"{args.api_url}/health", timeout=10)
        resp.raise_for_status()
        print(f"\nAPI health: {resp.json()}")
    except Exception as exc:
        print(f"\nERROR: Cannot reach API at {args.api_url}: {exc}")
        print("Make sure the backend is running:  python -m uvicorn src.api.app:app --port 8000")
        sys.exit(1)

    doc_ids = upload_batch(files, args.api_url, args.admin_key, batch_size=args.batch_size)

    if not doc_ids:
        print("\nNo documents were created — check error messages above.")
        sys.exit(1)

    if args.no_wait:
        print(f"\nUploaded {len(doc_ids)} doc(s). Jobs are running in the background.")
        print("Check status: GET /admin/jobs   (header X-Admin-Key: lexai-admin-secret)")
        return

    statuses = wait_for_jobs(doc_ids, args.api_url, args.admin_key)
    print_summary(statuses)

    failed = [d for d, s in statuses.items() if s in ("failed", "error")]
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
