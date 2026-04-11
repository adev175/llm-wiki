"""
LLM Wiki MCP Server
===================
Implements wiki_*, arxiv_*, and knowledge_search tools for the LLM Wiki vault.
Configure in Claude Desktop via claude_desktop_config.json.
"""

import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import httpx
import yaml
from mcp.server.fastmcp import FastMCP

# Load .env if present (python-dotenv optional)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Config — resolve vault relative to this file's parent
# ---------------------------------------------------------------------------
import os
_vault_override = os.environ.get("VAULT_ROOT")
VAULT_ROOT = Path(_vault_override) if _vault_override else Path(__file__).parent.parent / "vault"
WIKI_DIR = VAULT_ROOT / "wiki"
RAW_DIR = VAULT_ROOT / "raw"
PAPERS_DIR = VAULT_ROOT / "papers"
LOG_FILE = VAULT_ROOT / "log.md"
INDEX_FILE = WIKI_DIR / "_index.md"
LINT_FILE = WIKI_DIR / "_lint-report.md"

for d in (WIKI_DIR, RAW_DIR, PAPERS_DIR):
    d.mkdir(parents=True, exist_ok=True)

mcp = FastMCP("llm-wiki")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _append_log(entry: str) -> None:
    timestamp = _now()
    if not LOG_FILE.exists():
        LOG_FILE.write_text("# Activity Log\n\n")
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"\n- **{timestamp}** — {entry}\n")


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split YAML frontmatter from body. Returns (meta, body)."""
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            raw_yaml = text[3:end].strip()
            body = text[end + 3:].strip()
            try:
                meta = yaml.safe_load(raw_yaml) or {}
                return meta, body
            except Exception:
                pass
    return {}, text


def _slug_to_type(slug: str) -> str:
    """Derive type from slug prefix convention."""
    prefix_map = {
        "concept-": "concept",
        "strategy-": "strategy",
        "source-": "source",
        "entity-": "entity",
        "log-": "log",
        "paper-": "paper",
        "decision-": "decision",
        "kaizen-": "kaizen",
    }
    for prefix, t in prefix_map.items():
        if slug.startswith(prefix):
            return t
    return "note"


def _build_page(slug: str, title: str, content: str, tags: list[str],
                source: str, created: str | None = None,
                note_type: str | None = None,
                aliases: list[str] | None = None) -> str:
    today = _today()
    meta = {
        "title": title,
        "slug": slug,
        "type": note_type or _slug_to_type(slug),
        "tags": tags,
        "source": source,
        "created": created or today,
        "updated": _now(),
    }
    if aliases:
        meta["aliases"] = aliases
    fm = yaml.dump(meta, allow_unicode=True, default_flow_style=False).strip()
    return f"---\n{fm}\n---\n\n{content.strip()}\n"


def _all_wiki_pages() -> list[Path]:
    return [p for p in WIKI_DIR.glob("*.md") if not p.name.startswith("_")]


def _extract_wikilinks(text: str) -> list[str]:
    return re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", text)


# ---------------------------------------------------------------------------
# Wiki tools
# ---------------------------------------------------------------------------

@mcp.tool()
def wiki_write(slug: str, title: str, content: str,
               tags: list[str] | None = None, source: str = "manual",
               note_type: str | None = None,
               aliases: list[str] | None = None) -> str:
    """Create a new wiki page. Overwrites if slug already exists.

    Args:
        slug: kebab-case identifier, e.g. 'concept-momentum-trading'
        title: Human-readable title
        content: Markdown body (include [[wikilinks]])
        tags: List of tags, e.g. ['concept', 'trading']
        source: Origin of this content
        note_type: Explicit type override (auto-derived from slug prefix if omitted)
        aliases: Alternative names for search disambiguation, e.g. ['mean reversion', 'stat arb']
    """
    path = WIKI_DIR / f"{slug}.md"
    existed = path.exists()
    page = _build_page(slug, title, content, tags or [], source,
                       note_type=note_type, aliases=aliases)
    path.write_text(page, encoding="utf-8")
    action = "Updated" if existed else "Created"
    _append_log(f"{action} wiki page: `{slug}`")
    return f"✓ {action}: {slug}.md"


@mcp.tool()
def wiki_update(slug: str, new_content: str, source: str = "manual",
                mode: str = "merge") -> str:
    """Update an existing wiki page by appending or merging content.

    Args:
        slug: Page slug to update
        new_content: New information to add (Markdown)
        source: Origin of this update
        mode: 'append' to add section, 'merge' to synthesize (default)
    """
    path = WIKI_DIR / f"{slug}.md"
    if not path.exists():
        return f"✗ Not found: {slug}.md — use wiki_write to create it first."
    meta, body = _parse_frontmatter(path.read_text(encoding="utf-8"))
    meta["updated"] = _now()
    if source not in str(meta.get("source", "")):
        prev = meta.get("source", "")
        meta["source"] = f"{prev}, {source}".lstrip(", ")

    if mode == "append":
        body = body + f"\n\n---\n\n*Updated from {source} on {_today()}*\n\n{new_content.strip()}"
    else:
        body = body + f"\n\n## Update — {_today()} (source: {source})\n\n{new_content.strip()}"

    fm = yaml.dump(meta, allow_unicode=True, default_flow_style=False).strip()
    path.write_text(f"---\n{fm}\n---\n\n{body.strip()}\n", encoding="utf-8")
    _append_log(f"Updated wiki page: `{slug}` (source: {source})")
    return f"✓ Updated: {slug}.md"


@mcp.tool()
def wiki_read(slug: str) -> str:
    """Read a wiki page by slug.

    Args:
        slug: Page slug, e.g. 'concept-momentum-trading'
    """
    path = WIKI_DIR / f"{slug}.md"
    if not path.exists():
        return f"✗ Not found: {slug}.md"
    return path.read_text(encoding="utf-8")


@mcp.tool()
def wiki_delete(slug: str) -> str:
    """Delete a wiki page.

    Args:
        slug: Page slug to delete
    """
    path = WIKI_DIR / f"{slug}.md"
    if not path.exists():
        return f"✗ Not found: {slug}.md"
    path.unlink()
    _append_log(f"Deleted wiki page: `{slug}`")
    return f"✓ Deleted: {slug}.md"


@mcp.tool()
def wiki_list(tag: str = "") -> str:
    """List all wiki pages, optionally filtered by tag.

    Args:
        tag: Optional tag filter, e.g. 'concept' or 'strategy'
    """
    pages = _all_wiki_pages()
    results = []
    for p in sorted(pages):
        meta, _ = _parse_frontmatter(p.read_text(encoding="utf-8"))
        page_tags = meta.get("tags", [])
        if tag and tag not in page_tags:
            continue
        slug = meta.get("slug", p.stem)
        title = meta.get("title", slug)
        tags_str = ", ".join(page_tags)
        results.append(f"- [[{slug}]] — {title} `[{tags_str}]`")

    if not results:
        return "No pages found."
    header = f"**{len(results)} pages**" + (f" tagged `{tag}`" if tag else "") + "\n\n"
    return header + "\n".join(results)


@mcp.tool()
def wiki_search(query: str) -> str:
    """Full-text search across all wiki pages.

    Args:
        query: Search terms (case-insensitive)
    """
    query_lower = query.lower()
    hits = []
    for p in _all_wiki_pages():
        text = p.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(text)
        slug = meta.get("slug", p.stem)
        title = meta.get("title", slug)
        aliases = meta.get("aliases", [])

        # Check full text OR aliases
        alias_match = any(query_lower in a.lower() for a in aliases if isinstance(a, str))
        if query_lower in text.lower() or alias_match:
            match_note = " (alias match)" if alias_match and query_lower not in text.lower() else ""
            # Find first matching line in body
            for line in body.splitlines():
                if query_lower in line.lower():
                    snippet = line.strip()[:120]
                    hits.append(f"- [[{slug}]] — **{title}**{match_note}\n  > {snippet}")
                    break
            else:
                hints_str = f" [aliases: {', '.join(aliases[:3])}]" if aliases else ""
                hits.append(f"- [[{slug}]] — **{title}**{match_note}{hints_str} (match in frontmatter)")

    if not hits:
        return f"No results for: `{query}`"
    return f"**{len(hits)} results** for `{query}`:\n\n" + "\n\n".join(hits)


@mcp.tool()
def wiki_ingest_raw(filename: str, content: str) -> str:
    """Save raw source content to vault/raw/ (immutable store).

    Args:
        filename: Filename to save as, e.g. 'momentum-paper-2024.md'
        content: Raw text content
    """
    path = RAW_DIR / filename
    if path.exists():
        return f"✗ Already exists: raw/{filename} — raw/ is immutable."
    path.write_text(content, encoding="utf-8")
    _append_log(f"Ingested raw: `{filename}` ({len(content)} chars)")
    return f"✓ Saved to raw/{filename}"


@mcp.tool()
def wiki_rebuild_index() -> str:
    """Regenerate vault/wiki/_index.md catalog from all pages."""
    pages = _all_wiki_pages()
    by_tag: dict[str, list[str]] = {}
    all_entries = []

    for p in sorted(pages):
        meta, _ = _parse_frontmatter(p.read_text(encoding="utf-8"))
        slug = meta.get("slug", p.stem)
        title = meta.get("title", slug)
        tags = meta.get("tags", [])
        updated = meta.get("updated", "?")
        entry = f"- [[{slug}|{title}]] — `{updated}`"
        all_entries.append(entry)
        for t in tags:
            by_tag.setdefault(t, []).append(entry)

    lines = [
        "# Wiki Index",
        "",
        f"**Generated:** {_today()} | **Total Pages:** {len(pages)}",
        "",
        "## By Tag",
        "",
    ]
    for tag in sorted(by_tag):
        lines.append(f"### {tag}")
        lines.extend(by_tag[tag])
        lines.append("")

    lines += ["---", "", "## All Pages (alphabetical)", ""]
    lines.extend(all_entries)
    lines += ["", "---", f"", f"**Last rebuilt:** {_today()}"]

    INDEX_FILE.write_text("\n".join(lines), encoding="utf-8")
    _append_log(f"Rebuilt index ({len(pages)} pages)")
    return f"✓ Index rebuilt ({len(pages)} pages)"


@mcp.tool()
def wiki_lint() -> str:
    """Check vault health: broken wikilinks, orphan pages, missing frontmatter."""
    pages = _all_wiki_pages()
    slugs = {p.stem for p in pages}
    broken_links: dict[str, list[str]] = {}
    orphans: list[str] = []
    missing_fm: list[str] = []
    referenced: set[str] = set()

    for p in pages:
        text = p.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(text)
        slug = p.stem

        if not meta:
            missing_fm.append(slug)

        links = _extract_wikilinks(body)
        broken = [lnk for lnk in links if lnk not in slugs]
        if broken:
            broken_links[slug] = broken
        referenced.update(links)

    orphans = [p.stem for p in pages if p.stem not in referenced]

    report_lines = [
        "# Lint Report",
        "",
        f"**Generated:** {_today()}",
        "",
        "## Summary",
        f"- **Total pages:** {len(pages)}",
        f"- **Broken wikilinks:** {sum(len(v) for v in broken_links.values())}",
        f"- **Orphan pages:** {len(orphans)}",
        f"- **Missing frontmatter:** {len(missing_fm)}",
        "",
    ]

    if broken_links:
        report_lines += ["## Broken Wikilinks", ""]
        for page, links in broken_links.items():
            report_lines.append(f"- `{page}`: {', '.join(links)}")
        report_lines.append("")

    if orphans:
        report_lines += ["## Orphan Pages (not linked from anywhere)", ""]
        for o in orphans:
            report_lines.append(f"- [[{o}]]")
        report_lines.append("")

    if missing_fm:
        report_lines += ["## Missing Frontmatter", ""]
        for m in missing_fm:
            report_lines.append(f"- {m}.md")
        report_lines.append("")

    if not (broken_links or orphans or missing_fm):
        report_lines.append("## Status\n✓ Vault is healthy.")

    report_lines.append(f"\n---\n\n**Last checked:** {_today()}")
    report = "\n".join(report_lines)
    LINT_FILE.write_text(report, encoding="utf-8")

    summary = (
        f"✓ Lint done — {len(pages)} pages | "
        f"{sum(len(v) for v in broken_links.values())} broken links | "
        f"{len(orphans)} orphans | {len(missing_fm)} missing frontmatter"
    )
    return summary + "\n\n" + report


@mcp.tool()
def wiki_log(lines: int = 10) -> str:
    """Read the last N entries from vault/log.md.

    Args:
        lines: Number of log entries to return (default 10)
    """
    if not LOG_FILE.exists():
        return "Log is empty."
    entries = [l for l in LOG_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    return "\n".join(entries[-lines:])


# ---------------------------------------------------------------------------
# Inbox / capture tools
# ---------------------------------------------------------------------------

INBOX_DIR = VAULT_ROOT / "inbox"
INBOX_DIR.mkdir(parents=True, exist_ok=True)


@mcp.tool()
def wiki_capture(title: str, content: str, note_type: str = "log",
                 tags: list[str] | None = None) -> str:
    """Quick-capture a note to vault/inbox/ for later processing.
    Use when you want to capture an idea/insight without full analysis yet.

    Args:
        title: Brief title for the capture
        content: Note content (can be rough / unstructured)
        note_type: Rough type hint: 'log', 'concept', 'strategy', 'entity', etc.
        tags: Optional tags
    """
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower())[:40].strip("-")
    filename = f"{ts}-{slug}.md"
    path = INBOX_DIR / filename
    meta = {
        "title": title,
        "type": note_type,
        "tags": tags or [note_type],
        "captured": _now(),
        "status": "inbox",
    }
    fm = yaml.dump(meta, allow_unicode=True, default_flow_style=False).strip()
    path.write_text(f"---\n{fm}\n---\n\n{content.strip()}\n", encoding="utf-8")
    _append_log(f"Captured to inbox: `{filename}`")
    return f"✓ Captured: inbox/{filename}"


@mcp.tool()
def wiki_list_inbox() -> str:
    """List all notes in vault/inbox/ awaiting processing."""
    files = sorted(INBOX_DIR.glob("*.md"))
    if not files:
        return "✓ Inbox is empty."
    lines = [f"**{len(files)} item(s) in inbox:**\n"]
    for p in files:
        try:
            meta, _ = _parse_frontmatter(p.read_text(encoding="utf-8"))
            title = meta.get("title", p.stem)
            captured = meta.get("captured", "?")
            note_type = meta.get("type", "?")
            lines.append(f"- `{p.name}` — **{title}** [{note_type}] @ {captured}")
        except Exception:
            lines.append(f"- `{p.name}` (unreadable)")
    return "\n".join(lines)


@mcp.tool()
def wiki_daily(entry: str | None = None) -> str:
    """Read or append to today's daily research log (vault/wiki/log-<date>.md).
    If the daily note doesn't exist, creates it.

    Args:
        entry: Text to append to today's log. If None, returns current content.
    """
    today = _today()
    slug = f"log-{today}"
    path = WIKI_DIR / f"{slug}.md"

    if not path.exists():
        content = (
            f"## Research Log — {today}\n\n"
            f"*(Daily anchor for insights, captures, and decisions)*\n\n"
            f"### Session Notes\n\n"
        )
        page = _build_page(slug, f"Research Log {today}", content,
                           tags=["log", "daily"], source="wiki_daily",
                           note_type="daily")
        path.write_text(page, encoding="utf-8")
        _append_log(f"Created daily log: `{slug}`")

    if entry is None:
        return path.read_text(encoding="utf-8")

    # Append entry with timestamp
    current = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(current)
    meta["updated"] = _now()
    timestamp = datetime.now().strftime("%H:%M")
    body = body.rstrip() + f"\n- **{timestamp}** — {entry.strip()}\n"
    fm = yaml.dump(meta, allow_unicode=True, default_flow_style=False).strip()
    path.write_text(f"---\n{fm}\n---\n\n{body.strip()}\n", encoding="utf-8")
    _append_log(f"Appended to daily log: `{slug}`")
    return f"✓ Added to {slug}.md: {entry[:80]}"


# ---------------------------------------------------------------------------
# Arxiv tools
# ---------------------------------------------------------------------------

ARXIV_API = "https://export.arxiv.org/api/query"
ARXIV_NS = "http://www.w3.org/2005/Atom"


def _parse_arxiv_feed(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    ns = {"atom": ARXIV_NS, "arxiv": "http://arxiv.org/schemas/atom"}
    papers = []
    for entry in root.findall("atom:entry", ns):
        def get(tag: str) -> str:
            el = entry.find(tag, ns)
            return el.text.strip() if el is not None and el.text else ""

        arxiv_id_raw = get("atom:id")
        arxiv_id = arxiv_id_raw.split("/abs/")[-1].replace("/", "_")
        authors = [
            a.find("atom:name", ns).text.strip()
            for a in entry.findall("atom:author", ns)
            if a.find("atom:name", ns) is not None
        ]
        categories = [
            c.get("term", "")
            for c in entry.findall("atom:category", ns)
        ]
        papers.append({
            "id": arxiv_id,
            "title": get("atom:title").replace("\n", " "),
            "summary": get("atom:summary").replace("\n", " "),
            "authors": authors,
            "published": get("atom:published")[:10],
            "updated": get("atom:updated")[:10],
            "categories": categories,
            "url": arxiv_id_raw,
            "pdf_url": arxiv_id_raw.replace("/abs/", "/pdf/"),
        })
    return papers


@mcp.tool()
def arxiv_search(query: str, max_results: int = 5,
                 sort_by: str = "relevance") -> str:
    """Search Arxiv for papers related to a query.

    Args:
        query: Search terms, e.g. 'momentum trading machine learning'
        max_results: Number of results (default 5, max 20)
        sort_by: 'relevance' or 'lastUpdatedDate' or 'submittedDate'
    """
    max_results = min(max_results, 20)
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": sort_by,
        "sortOrder": "descending",
    }
    try:
        r = httpx.get(ARXIV_API, params=params, timeout=15)
        r.raise_for_status()
        papers = _parse_arxiv_feed(r.text)
    except Exception as e:
        return f"✗ Arxiv API error: {e}"

    if not papers:
        return f"No papers found for: `{query}`"

    lines = [f"**{len(papers)} papers** for `{query}`:\n"]
    for p in papers:
        authors_str = ", ".join(p["authors"][:3])
        if len(p["authors"]) > 3:
            authors_str += " et al."
        lines.append(
            f"**{p['title']}**\n"
            f"  ID: `{p['id']}` | {p['published']} | {authors_str}\n"
            f"  {p['summary'][:200]}…\n"
            f"  URL: {p['url']}\n"
        )
    return "\n".join(lines)


@mcp.tool()
def arxiv_fetch_paper(arxiv_id: str, save: bool = True) -> str:
    """Fetch full metadata for an Arxiv paper and optionally save to vault/papers/.

    Args:
        arxiv_id: Arxiv paper ID, e.g. '2401.12345' or '2401.12345v2'
        save: Whether to save the paper as a wiki page in vault/papers/ (default True)
    """
    clean_id = arxiv_id.strip().replace("_", "/")
    params = {"id_list": clean_id, "max_results": 1}
    try:
        r = httpx.get(ARXIV_API, params=params, timeout=15)
        r.raise_for_status()
        papers = _parse_arxiv_feed(r.text)
    except Exception as e:
        return f"✗ Arxiv API error: {e}"

    if not papers:
        return f"✗ Paper not found: {arxiv_id}"

    p = papers[0]
    slug = f"paper-{p['id'].replace('/', '-').replace('.', '-')}"
    authors_str = ", ".join(p["authors"])
    categories_str = ", ".join(p["categories"])

    content = f"""## Abstract

{p['summary']}

## Metadata

| Field | Value |
|-------|-------|
| **Authors** | {authors_str} |
| **Published** | {p['published']} |
| **Updated** | {p['updated']} |
| **Categories** | {categories_str} |
| **Arxiv URL** | [{p['url']}]({p['url']}) |
| **PDF** | [{p['pdf_url']}]({p['pdf_url']}) |

## Key Concepts

*(Add extracted concepts here after reading the paper)*

## Practical Considerations

*(Add trading/implementation notes here)*

## Related Wiki Pages

*(Link relevant wiki pages here, e.g. [[concept-momentum-trading]])*
"""

    if save:
        meta = {
            "title": p["title"],
            "slug": slug,
            "tags": ["source", "paper"] + [c.split(".")[0].lower() for c in p["categories"][:2]],
            "arxiv_id": clean_id,
            "authors": p["authors"],
            "published": p["published"],
            "source": f"arxiv:{clean_id}",
            "created": _today(),
            "updated": _now(),
        }
        fm = yaml.dump(meta, allow_unicode=True, default_flow_style=False).strip()
        page = f"---\n{fm}\n---\n\n{content.strip()}\n"
        out_path = PAPERS_DIR / f"{slug}.md"
        out_path.write_text(page, encoding="utf-8")
        _append_log(f"Fetched Arxiv paper: `{clean_id}` → `papers/{slug}.md`")
        return f"✓ Saved: papers/{slug}.md\n\n**{p['title']}**\n{p['summary'][:300]}…"
    else:
        return f"**{p['title']}**\n\n{content}"


# ---------------------------------------------------------------------------
# Knowledge auto-search tool
# ---------------------------------------------------------------------------

@mcp.tool()
def knowledge_search(topic: str, save_if_useful: bool = True,
                     min_length: int = 200) -> str:
    """Search Arxiv + Hugging Face for knowledge related to a topic.
    If the result is meaningful (length > min_length), save as a wiki page.

    Args:
        topic: Topic to research, e.g. 'walk-forward validation overfitting'
        save_if_useful: Auto-save to wiki if content is substantive (default True)
        min_length: Minimum char length to consider content 'useful' (default 200)
    """
    results_parts = []

    # 1. Search Arxiv
    try:
        params = {
            "search_query": f"all:{topic}",
            "start": 0,
            "max_results": 3,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        r = httpx.get(ARXIV_API, params=params, timeout=15)
        r.raise_for_status()
        papers = _parse_arxiv_feed(r.text)
        if papers:
            paper_lines = [f"### Arxiv Papers for `{topic}`\n"]
            for p in papers:
                authors_short = ", ".join(p["authors"][:2])
                paper_lines.append(
                    f"- **{p['title']}** ({authors_short}, {p['published']})\n"
                    f"  ID: `{p['id']}` — {p['summary'][:150]}…"
                )
            results_parts.append("\n".join(paper_lines))
    except Exception as e:
        results_parts.append(f"*Arxiv search failed: {e}*")

    combined = "\n\n".join(results_parts)

    if not combined.strip():
        return f"No useful results found for: `{topic}`"

    # 2. Decide whether to save
    if save_if_useful and len(combined) >= min_length:
        slug = "log-" + _today() + "-" + re.sub(r"[^a-z0-9]+", "-", topic.lower())[:40].strip("-")
        title = f"Knowledge Search: {topic}"
        content = (
            f"*Auto-captured via knowledge_search on {_today()}*\n\n"
            f"## Search Results\n\n{combined}\n\n"
            f"## Summary\n\n*(Synthesize key takeaways here)*\n\n"
            f"## Related Pages\n\n*(Link relevant wiki pages)*"
        )
        page = _build_page(slug, title, content,
                           tags=["log", "research"], source=f"knowledge_search:{topic}")
        (WIKI_DIR / f"{slug}.md").write_text(page, encoding="utf-8")
        _append_log(f"Auto-saved knowledge search: `{topic}` → `{slug}.md`")
        return f"✓ Saved: wiki/{slug}.md\n\n{combined}"

    return combined


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
