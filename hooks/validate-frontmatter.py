#!/usr/bin/env python3
"""
validate-frontmatter.py — Validate frontmatter schema for LLM Wiki pages.

Used as a Claude Code PreToolUse hook or run standalone to audit the vault.
Checks required fields, valid tag conventions, slug prefix alignment.

Usage:
    python validate-frontmatter.py /path/to/vault/wiki
    python validate-frontmatter.py /path/to/specific-file.md
    echo $? # 0 = ok, 1 = errors found
"""

import sys
import yaml
from pathlib import Path

VALID_TYPES = {
    "concept", "strategy", "source", "entity", "log", "paper",
    "decision", "kaizen", "note", "daily",
}

VALID_SLUG_PREFIXES = (
    "concept-", "strategy-", "source-", "entity-", "log-",
    "paper-", "decision-", "kaizen-",
)

REQUIRED_FIELDS = ["title", "slug", "tags", "source", "created"]

VALID_TAGS = {
    "source", "concept", "entity", "strategy", "log",
    "trading", "quant", "risk", "ml", "data", "macro",
    "paper", "kaizen", "standard", "backlog", "idea",
    "automation", "search", "daily",
}


def parse_frontmatter(filepath: Path) -> tuple[dict | None, list[str]]:
    errors = []
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return None, [f"Cannot read file: {e}"]

    if not content.startswith("---"):
        return None, ["Missing frontmatter (file doesn't start with ---)"]

    end = content.find("---", 3)
    if end == -1:
        return None, ["Malformed frontmatter (no closing ---)"]

    try:
        fm = yaml.safe_load(content[3:end])
    except yaml.YAMLError as e:
        return None, [f"Invalid YAML in frontmatter: {e}"]

    if not isinstance(fm, dict):
        return None, ["Frontmatter is not a valid YAML mapping"]

    return fm, errors


def validate_note(filepath: Path) -> list[str]:
    errors = []
    fm, parse_errors = parse_frontmatter(filepath)
    errors.extend(parse_errors)
    if fm is None:
        return errors

    # Required fields
    for field in REQUIRED_FIELDS:
        if field not in fm:
            errors.append(f"Missing required field: '{field}'")

    # type field
    note_type = fm.get("type", "")
    if note_type and note_type not in VALID_TYPES:
        errors.append(f"Invalid type: '{note_type}'. Valid: {sorted(VALID_TYPES)}")

    # tags must be a list
    tags = fm.get("tags")
    if tags is not None and not isinstance(tags, list):
        errors.append("'tags' must be a YAML list, not a string")

    # slug format: kebab-case
    slug = fm.get("slug", "")
    if slug and not all(c.islower() or c.isdigit() or c == "-" for c in slug):
        errors.append(f"Slug '{slug}' must be kebab-case (lowercase, hyphens only)")

    # aliases must be a list if present
    aliases = fm.get("aliases")
    if aliases is not None and not isinstance(aliases, list):
        errors.append("'aliases' must be a YAML list")

    return errors


def validate_path(target: Path) -> int:
    if target.is_file():
        files = [target]
    else:
        files = sorted(target.glob("*.md"))
        files = [f for f in files if not f.stem.startswith("_")]

    total_errors = 0
    for filepath in files:
        errors = validate_note(filepath)
        if errors:
            rel = filepath.name
            print(f"\n❌ {rel}")
            for err in errors:
                print(f"   • {err}")
                total_errors += 1

    if total_errors == 0:
        print("✅ All wiki pages have valid frontmatter")
    else:
        print(f"\n{total_errors} error(s) across {len(files)} file(s)")

    return total_errors


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate-frontmatter.py /path/to/vault/wiki")
        sys.exit(1)

    target = Path(sys.argv[1]).resolve()
    if not target.exists():
        print(f"Error: {target} does not exist")
        sys.exit(1)

    sys.exit(1 if validate_path(target) > 0 else 0)
