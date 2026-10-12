#!/usr/bin/env python3
"""Cheap secrets/token scanner used by pre-commit.

Scans tracked files for common credential markers (GitHub PATs, cloud keys,
API keys) and, when a git-ignored termlist exists under $SECRET_TERMS_FILE or
.secret-terms, greps that too. The banned-terms list itself stays OUT of the
repo per PLAN M0 (it may contain your own names/keywords — never commit it).

Exits non-zero on any hit so the author must resolve the leak before committing.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import unicodedata
from pathlib import Path

TOKEN_PATTERNS = [
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),  # GitHub PATs / OAuth / user
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),          # OpenAI-style keys
    re.compile(r"\bAIza[0-9A-Za-z_\-]{20,}\b"),      # Google API keys
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),             # AWS access key ids
    re.compile(r"\b(?:xox[baprs]-|xoxr-)[A-Za-z0-9\-]+"),  # Slack
    re.compile(r"\bSAP[A-Z0-9\-_/]{20,}\b"),         # SAP env markers (assumption: e.g. SAP_JWT)
]

SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", "evals/cache",
             "models/artifacts", ".github"}
SKIP_FILES = {".gitignore", ".secret-terms", "requirements.lock"}


def _iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        rel = Path(path.relative_to(root))
        top = rel.parts[0] if rel.parts else ""
        if path.is_file() and top not in SKIP_DIRS and path.name not in SKIP_FILES:
            files.append(path)
    return files


def _safe_read(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return unicodedata.normalize("NFC", text)
    except OSError:
        return ""


def scan_files(files: list[Path]) -> list[tuple[Path, str]]:
    hits: list[tuple[Path, str]] = []
    for path in files:
        text = _safe_read(path)
        for pattern in TOKEN_PATTERNS:
            for match in pattern.finditer(text):
                hits.append((path, match.group(0)))
    return hits


def scan_term_list(text: str, root: Path) -> list[tuple[Path, str]]:
    terms = [line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#")]
    if not terms:
        return []
    hits: list[tuple[Path, str]] = []
    compiled = [re.compile(re.escape(term), re.IGNORECASE) for term in terms]
    for path in _iter_files(root):
        body = _safe_read(path)
        if any(regex.search(body) for regex in compiled):
            hits.append((path, "<banned term>"))
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args(argv)

    root = Path(args.root)
    hits = scan_files(_iter_files(root))

    term_file = os.environ.get("SECRET_TERMS_FILE") or (root / ".secret-terms")
    if term_file and Path(term_file).is_file():
        hits += scan_term_list(Path(term_file).read_text(encoding="utf-8", errors="ignore"), root)

    if not hits:
        return 0
    for path, marker in hits:
        print(f"SECRET CHECK FAILED: {path} contains {marker}", file=sys.stderr)
    print(
        "Resolve the finding, then rotate anything that was already exposed.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())