#!/usr/bin/env python3
"""
update-modified.py — Auto-update the 'updated' field in wiki page frontmatter.

Used as a Claude Code PostToolUse hook. Runs after any Edit/Write to a .md
file in vault/wiki/ or vault/papers/, keeping the updated timestamp accurate
without relying on the LLM to remember.

Usage:
    python update-modified.py /path/to/note.md
"""

import sys
import re
from datetime import datetime
from pathlib import Path


def update_modified(filepath: str) -> None:
    path = Path(filepath)
    if not path.exists() or path.suffix != ".md":
        return

    # Only process vault pages, skip _index and _lint-report
    if path.stem.startswith("_"):
        return

    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return

    end = content.find("---", 3)
    if end == -1:
        return

    frontmatter = content[3:end]
    body = content[end:]
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if re.search(r"^updated:", frontmatter, re.MULTILINE):
        frontmatter = re.sub(
            r"^updated:.*$",
            f"updated: '{now}'",
            frontmatter,
            flags=re.MULTILINE,
        )
    else:
        frontmatter = frontmatter.rstrip() + f"\nupdated: '{now}'\n"

    path.write_text(f"---{frontmatter}{body}", encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        update_modified(sys.argv[1])
