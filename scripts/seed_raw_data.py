#!/usr/bin/env python3
"""
Seed ALL built-in knowledge into LexAI — one command, everything seeded.

Step 1 — Metadata (instant): POST /admin/seed
  Seeds templates, TT55 official forms, risks, checklists, and legal cases
  into MongoDB so the system has built-in knowledge immediately.

Step 2 — Raw documents (background jobs): POST /admin/documents/upload
  Discovers all .doc / .docx / .pdf files under raw_data/ (skips dataset
  sub-directories and duplicate downloads like 'file (1).doc'), uploads them
  via the admin API, then polls until every job reaches a terminal state.

Usage:
    python scripts/seed_raw_data.py
    python scripts/seed_raw_data.py --api-url http://localhost:8000 --admin-key lexai-admin-secret
    python scripts/seed_raw_data.py --dry-run          # list files only, no upload
    python scripts/seed_raw_data.py --no-wait          # upload files and exit immediately
    python scripts/seed_raw_data.py --force            # re-upload files already in DB
    python scripts/seed_raw_data.py --skip-metadata    # skip Step 1 (templates/forms)
    python scripts/seed_raw_data.py --skip-files       # skip Step 2 (raw documents)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: 'requests' is not installed.  Run:  pip install requests")
    sys.exit(1)

_DEFAULT_API_URL   = os.environ.get("API_URL", "http://localhost:8000")
_DEFAULT_ADMIN_KEY = os.environ.get("ADMIN_API_KEY", "lexai-admin-secret")
_RAW_DATA_DIR      = Path(__file__).parent.parent / "raw_data"
_POLL_INTERVAL_S   = 5
_MAX_WAIT_S        = 600   # 10 minutes total
_EXTENSIONS        = {".doc", ".docx", ".pdf", ".html"}

# Sub-directories under raw_data/ that are dataset/corpus dirs, not legal texts.
_EXCLUDE_DIRS = {"VNLegalText-main", "bm25_legal_corpus"}

# Pattern for Windows duplicate downloads: "file (1).doc", "file (2).doc"
_DUPLICATE_RE = re.compile(r" \(\d+\)$")


def seed_metadata(api_url: str, admin_key: str) -> bool:
    """Call POST /admin/seed to upsert built-in templates, forms, risks, checklists."""
    print("\n-- Step 1: Seeding built-in metadata (templates / TT55 forms / risks) --")
    try:
        resp = requests.post(
            f"{api_url}/admin/seed",
            headers={"X-Admin-Key": admin_key},
            timeout=120,
        )
    except Exception as exc:
        print(f"  ERROR: could not reach /admin/seed — {exc}")
        return False

    if resp.status_code in (200, 202):
        data = resp.json()
        print("  OK -- seeded:")
        for k, v in data.items():
            print(f"    {k}: {v}")
        return True
    else:
        print(f"  ERROR {resp.status_code}: {resp.text[:300]}")
        return False


def discover_files(root: Path) -> list[Path]:
    """Return sorted list of uploadable legal document files."""
    found: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in _EXTENSIONS:
            continue
        # Skip Office temporary/lock files, e.g. "~$document.doc".
        if p.name.startswith("~$"):
            continue
        # Skip excluded dataset directories
        if any(ex in p.parts for ex in _EXCLUDE_DIRS):
            continue
        # Skip Windows duplicate downloads ("file (1).doc")
        stem = p.stem
        if _DUPLICATE_RE.search(stem):
            continue
        found.append(p)
    found.sort()
    return found


def get_existing_filenames(api_url: str, admin_key: str) -> set[str]:
    """Fetch filenames already registered in the admin document list."""
    try:
        resp = requests.get(
            f"{api_url}/admin/documents",
            headers={"X-Admin-Key": admin_key},
            params={"limit": 500},
            timeout=30,
        )
        if resp.status_code == 200:
            return {d["filename"] for d in resp.json()}
    except Exception as exc:
        print(f"  WARNING: could not fetch existing documents: {exc}")
    return set()


def upload_batch(
    files: list[Path],
    api_url: str,
    admin_key: str,
    batch_size: int = 3,
) -> list[str]:
    """Upload files in batches. Returns list of doc_ids created."""
    doc_ids: list[str] = []
    total = len(files)

    for i in range(0, total, batch_size):
        batch = files[i : i + batch_size]
        print(f"\n[{i + 1}–{min(i + batch_size, total)}/{total}] Uploading …")

        file_handles = []
        try:
            for fp in batch:
                fh = open(fp, "rb")
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

        if resp.status_code not in (200, 201, 202):
            print(f"  ERROR {resp.status_code}: {resp.text[:300]}")
            continue

        data = resp.json()
        # API returns AdminUploadResult: {"uploaded": [...], "errors": [...]}
        batch_ids = [d["doc_id"] for d in data.get("uploaded", [])]
        doc_ids.extend(batch_ids)

        errors = data.get("errors", [])
        if errors:
            for e in errors:
                print(f"  SKIP {e.get('filename')}: {e.get('error')}")

        print(f"  Created {len(batch_ids)} document(s)")

    return doc_ids


def wait_for_jobs(
    doc_ids: list[str],
    api_url: str,
    admin_key: str,
    max_wait_s: int = _MAX_WAIT_S,
    poll_s: int = _POLL_INTERVAL_S,
) -> dict[str, str]:
    """Poll /admin/jobs until all doc_ids reach terminal status."""
    if not doc_ids:
        return {}

    print(f"\nWaiting for {len(doc_ids)} job(s) to complete (max {max_wait_s}s) …")
    # Terminal states from job_runner.py: "complete" and "failed"
    terminal = {"complete", "failed"}
    statuses: dict[str, str] = {d: "pending" for d in doc_ids}
    deadline = time.monotonic() + max_wait_s

    while time.monotonic() < deadline:
        try:
            resp = requests.get(
                f"{api_url}/admin/jobs",
                headers={"X-Admin-Key": admin_key},
                params={"limit": 500},
                timeout=30,
            )
        except Exception as exc:
            print(f"  Poll error: {exc}")
            time.sleep(poll_s)
            continue

        if resp.status_code != 200:
            print(f"  Poll error {resp.status_code}: {resp.text[:200]}")
            time.sleep(poll_s)
            continue

        # Endpoint returns a list directly (not wrapped in {"jobs": [...]})
        jobs = resp.json()
        if isinstance(jobs, dict):
            jobs = jobs.get("jobs", [])

        for job in jobs:
            doc_id = job.get("doc_id")
            if doc_id in statuses:
                statuses[doc_id] = job.get("status", "unknown")

        pending = [d for d, s in statuses.items() if s not in terminal]
        done = len(statuses) - len(pending)
        print(f"  {done}/{len(statuses)} done — still running: {len(pending)}")

        if not pending:
            break
        time.sleep(poll_s)
    else:
        print("  WARNING: timeout reached — some jobs may still be running.")

    return statuses


def print_summary(statuses: dict[str, str]) -> None:
    from collections import Counter
    print("\n" + "=" * 60)
    print("SEED SUMMARY")
    print("=" * 60)
    counts = Counter(statuses.values())
    for st, count in sorted(counts.items()):
        mark = "OK" if st == "complete" else "!!" if st == "failed" else "??"
        print(f"  {mark}  {st}: {count}")
    failed = [d for d, s in statuses.items() if s == "failed"]
    if failed:
        print(f"\nFailed ({len(failed)}):")
        for d in failed:
            print(f"  - {d}")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed raw Vietnamese legal documents into the LexAI admin API."
    )
    parser.add_argument("--api-url",    default=_DEFAULT_API_URL,   help="Backend base URL")
    parser.add_argument("--admin-key",  default=_DEFAULT_ADMIN_KEY, help="Admin API key")
    parser.add_argument("--batch-size", type=int, default=3,        help="Files per upload request")
    parser.add_argument("--no-wait",       action="store_true", help="Upload files and exit; skip polling")
    parser.add_argument("--dry-run",       action="store_true", help="List files only, no upload")
    parser.add_argument("--force",         action="store_true", help="Re-upload even if filename already in DB")
    parser.add_argument("--skip-metadata", action="store_true", help="Skip Step 1 — do not call /admin/seed")
    parser.add_argument("--skip-files",    action="store_true", help="Skip Step 2 — do not upload raw documents")
    args = parser.parse_args()

    print("LexAI — Full Knowledge Seeder")
    print(f"  API:      {args.api_url}")
    print(f"  data dir: {_RAW_DATA_DIR}")

    if args.dry_run:
        files = discover_files(_RAW_DATA_DIR)
        print(f"\nFound {len(files)} file(s) in raw_data/:")
        for f in files:
            print(f"  {f.relative_to(_RAW_DATA_DIR.parent)}")
        print("\n[dry-run] No data uploaded.")
        return

    # Verify API is reachable
    try:
        resp = requests.get(f"{args.api_url}/health", timeout=10)
        resp.raise_for_status()
        print(f"\nAPI health: {resp.json()}")
    except Exception as exc:
        print(f"\nERROR: Cannot reach API at {args.api_url}: {exc}")
        print("Make sure the backend is running first.")
        sys.exit(1)

    # -- Step 1: seed built-in metadata -------------------------------------
    if not args.skip_metadata:
        seed_metadata(args.api_url, args.admin_key)
    else:
        print("\n-- Step 1: skipped (--skip-metadata) --")

    # -- Step 2: upload raw documents ----------------------------------------
    if args.skip_files:
        print("\n-- Step 2: skipped (--skip-files) --")
        return

    print("\n-- Step 2: Uploading raw legal documents --")
    files = discover_files(_RAW_DATA_DIR)
    if not files:
        print("  No .doc/.docx/.pdf/.html files found in raw_data/")
        return

    print(f"\nFound {len(files)} file(s):")
    for f in files:
        print(f"  {f.relative_to(_RAW_DATA_DIR.parent)}")

    # Idempotency: skip files already in DB
    if not args.force:
        existing = get_existing_filenames(args.api_url, args.admin_key)
        if existing:
            before = len(files)
            files = [f for f in files if f.name not in existing]
            skipped = before - len(files)
            if skipped:
                print(f"\nSkipping {skipped} file(s) already in database (use --force to re-upload).")
        if not files:
            print("\nAll files already seeded. Nothing to do.")
            return

    print(f"\nUploading {len(files)} file(s) …")
    doc_ids = upload_batch(files, args.api_url, args.admin_key, batch_size=args.batch_size)

    if not doc_ids:
        print("\nNo documents were created — check error messages above.")
        sys.exit(1)

    if args.no_wait:
        print(f"\nQueued {len(doc_ids)} doc(s). Jobs are processing in the background.")
        return

    statuses = wait_for_jobs(doc_ids, args.api_url, args.admin_key)
    print_summary(statuses)

    failed = [d for d, s in statuses.items() if s == "failed"]
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
