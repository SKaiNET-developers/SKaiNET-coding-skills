#!/usr/bin/env python3
"""
Verify every `// from: <path>:<lines>` citation across every SKILL.md and
reference markdown resolves to a real file in the SKaiNET clone.

Looks for SKaiNET as a sibling directory (../SKaiNET) by default.
Override with --skainet-root.

Usage:
    python3 tools/verify-citations.py
    python3 tools/verify-citations.py --skainet-root /path/to/SKaiNET

Exits non-zero if any citation is missing or out of range.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

CITE_RE = re.compile(
    r"from:\s+(SKaiNET/[^\s]+\.(?:kts|kt|java|toml))(?::(\d+)(?:-(\d+))?)?"
)

PLUGIN_DIRS = ["skainet-contributor-skills/skills", "skainet-consumer-skills/skills"]


def collect_citations(repo_root: Path) -> list[tuple[str, str | None, str | None, Path]]:
    cites: set[tuple[str, str | None, str | None, str]] = set()
    for rel in PLUGIN_DIRS:
        root = repo_root / rel
        if not root.is_dir():
            continue
        for path in root.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            for m in CITE_RE.finditer(text):
                cites.add((m.group(1), m.group(2), m.group(3), str(path)))
    return [(p, s, e, Path(src)) for (p, s, e, src) in sorted(cites)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skainet-root",
        type=Path,
        default=None,
        help="Path to SKaiNET clone. Defaults to ../SKaiNET relative to this repo.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Path to skainet-coding-skills repo root. Defaults to the parent of this script's directory.",
    )
    args = parser.parse_args()

    repo_root: Path = args.repo_root.resolve()
    skainet_root: Path = (args.skainet_root or repo_root.parent / "SKaiNET").resolve()

    if not skainet_root.is_dir():
        print(
            f"ERROR: SKaiNET clone not found at {skainet_root}.\n"
            f"Clone it as a sibling of this repo or pass --skainet-root.",
            file=sys.stderr,
        )
        return 2

    cites = collect_citations(repo_root)
    if not cites:
        print("No citations found — nothing to check.", file=sys.stderr)
        return 0

    errors = 0
    for cited_rel, start, end, src in cites:
        # cited_rel is "SKaiNET/<rest>"; resolve against the parent of skainet_root
        target = skainet_root.parent / cited_rel
        if not target.is_file():
            print(f"MISSING: {cited_rel}  (in {src.relative_to(repo_root)})")
            errors += 1
            continue
        if start:
            with target.open(encoding="utf-8") as f:
                n = sum(1 for _ in f)
            s = int(start)
            e = int(end) if end else s
            if e > n:
                print(
                    f"OUT-OF-RANGE: {cited_rel}:{start}-{end or start} "
                    f"(file has {n} lines)  (in {src.relative_to(repo_root)})"
                )
                errors += 1

    total = len(cites)
    if errors:
        print(f"\n{total} citations checked; {errors} problem(s).", file=sys.stderr)
        return 1
    print(f"{total} citations checked; all OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
