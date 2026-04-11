# TO-BE — Hệ thống cải thiện được đề xuất

> Dựa trên gap analysis từ audit AS-IS và mục tiêu Idea ban đầu.
> Priority được sắp xếp từ impactful nhất đến enhancement.

---

## Vision

Biến llm-wiki từ **manual tool** thành **living knowledge system** — nơi knowledge tự động được capture, synthesize, và maintain health mà không cần user can thiệp liên tục.

---

## Architecture TO-BE

```
┌──────────────────────────────────────────────────────────────────┐
│           Claude Desktop              Claude.ai (web)            │
└──────────────┬────────────────────────────────┬─────────────────┘
               │ stdio MCP                      │ HTTP/SSE MCP
               ▼                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                    MCP Server (Enhanced)                         │
│                                                                  │
│  Wiki Tools (existing)    New Tools:                            │
│  + wiki_write             + wiki_write_safe (no-overwrite)      │
│  + wiki_search            + wiki_semantic_search (embeddings)   │
│  + wiki_lint              + wiki_auto_fix (lint + fix)          │
│  + knowledge_search       + web_search (Tavily/Brave API)       │
│                           + wiki_export (markdown/JSON)         │
│                           + wiki_stats (dashboard)              │
└──────────────┬───────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────┐
│                    vault/ (Enhanced)                             │
│  inbox/   raw/    01-daily/ … 10-kaizen/   papers/   log.md    │
│           (imm.)  [typed subfolders]        + summaries/        │
│           embeddings/ (*.npy / SQLite vec)  + stats.json        │
└──────────────────────────────────────────────────────────────────┘
               │
               ▼ (optional)
┌──────────────────────────────────────────────────────────────────┐
│              Scheduled Tasks (Windows Task Scheduler)            │
│  - Daily: wiki_lint + auto_fix + rebuild_index                  │
│  - Weekly: knowledge_refresh (re-check trending topics)         │
└──────────────────────────────────────────────────────────────────┘
```

---

## Priority 1 — Critical (Phải có)

### P1.1 — Seed vault với content thực tế

**Problem:** Vault rỗng = không validate được gì.

**Solution:**
1. Tạo ít nhất 5-10 trang mẫu từ conversations thực tế
2. Ingest ít nhất 1 raw source (Ernie Chan book notes, article)
3. Fetch ít nhất 2-3 Arxiv papers liên quan

**Implementation:** Manual bước đầu, sau đó hệ thống tự chạy.
```bash
# Bước 1: Seed nhanh
# Dùng Claude Desktop với CLAUDE.md → gọi wiki_write cho 5 concept pages
# Dùng arxiv_fetch_paper cho 3 papers quant trading
```

**Expected outcome:** Vault có ≥10 pages → lint, search, index có data để test.

---

### P1.2 — `wiki_write_safe` — Không overwrite silent

**Problem:** `wiki_write` overwrite toàn bộ content mà không cảnh báo.

**Solution:** Tool mới với write modes:
```python
@mcp.tool()
def wiki_write_safe(slug: str, title: str, content: str,
                    tags: list[str] | None = None,
                    source: str = "manual",
                    mode: str = "create_only") -> str:
    """
    mode:
    - 'create_only': fail nếu slug đã tồn tại
    - 'merge': append update section (gọi wiki_update internally)
    - 'overwrite': hành vi cũ (explicit)
    """
```

**Migration:** Đổi default behavior của `wiki_write` → thêm warning khi overwrite.

---

### P1.3 — Fix CLAUDE.md — Conversation Capture Enforcement

**Problem:** Auto-capture là soft suggestion, không được enforce.

**Solution:** Thêm vào CLAUDE.md một **structured trigger** rõ ràng hơn:

```markdown
## MANDATORY: End-of-Response Capture Check

**SAU MỖI response dài hơn 5 câu**, bắt buộc chạy internal checklist:
[ ] Có concept mới chưa có trong wiki?  → wiki_write("concept-...")
[ ] Có insight về strategy/risk? → wiki_write hoặc wiki_update
[ ] User đề cập tên người/tool/sách? → kiểm tra hoặc tạo entity page
[ ] Câu trả lời này có thể apply cho session khác? → wiki_write("log-...")

Nếu ≥1 checkbox TRUE → file it. Không hỏi user.
```

**Thêm vào Anti-patterns:**
```
❌ Kết thúc response mà không check capture checklist
```

---

### P1.4 — Fix `knowledge_search` — Thêm web search

**Problem:** Docstring nói "Arxiv + Hugging Face" nhưng chỉ có Arxiv.

**Solution A (minimal):** Thêm Wikipedia API:
```python
# Thêm Wikipedia search
WIKI_API = "https://en.wikipedia.org/api/rest_v1/page/summary/{topic}"
```

**Solution B (recommended):** Tích hợp Brave Search API hoặc Tavily:
```python
# Thêm vào requirements.txt: tavily-python
from tavily import TavilyClient

def _search_web(query: str, max_results: int = 3) -> list[dict]:
    client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    return client.search(query, max_results=max_results)["results"]
```

**Config:** Thêm `TAVILY_API_KEY` vào env hoặc `claude_desktop_config.json`.

---

## Priority 2 — Important (Nên có)

### P2.1 — Semantic Search với Embeddings

**Problem:** `wiki_search` chỉ substring match — miss các query tương đồng.

**Solution:** Dùng SQLite với `sqlite-vec` extension hoặc file-based embeddings:

```python
# Option 1: Local embeddings với sentence-transformers
# requirements.txt thêm: sentence-transformers

from sentence_transformers import SentenceTransformer
import numpy as np

MODEL = SentenceTransformer("all-MiniLM-L6-v2")  # 80MB, offline

EMBED_DIR = VAULT_ROOT / "embeddings"

@mcp.tool()
def wiki_semantic_search(query: str, top_k: int = 5) -> str:
    """Semantic search using sentence embeddings."""
    q_vec = MODEL.encode(query)
    # Load precomputed embeddings, cosine similarity
    results = _cosine_search(q_vec, top_k)
    return _format_results(results)
```

**Alternative (simpler):** Gọi Claude API để re-rank kết quả từ `wiki_search`.

---

### P2.2 — HTTP/SSE Transport để support Claude.ai web

**Problem:** MCP stdio chỉ cho Desktop. Idea đề cập "Claude.ai" nhưng không được support.

**Solution:** Thêm HTTP transport song song:
```python
# server.py — thêm web server mode
import uvicorn
from mcp.server.sse import SseServerTransport

if __name__ == "__main__":
    mode = os.getenv("MCP_TRANSPORT", "stdio")
    if mode == "http":
        # Expose qua HTTP (cần auth nếu public)
        transport = SseServerTransport("/messages")
        uvicorn.run(mcp.get_asgi_app(), host="0.0.0.0", port=8000)
    else:
        mcp.run(transport="stdio")
```

**Config Claude.ai:** Remote MCP endpoint (khi Claude.ai hỗ trợ custom MCP).

**Note:** Cần auth layer (API key) nếu expose ra internet.

---

### P2.3 — `wiki_auto_fix` — Lint + Auto-repair

**Problem:** `wiki_lint` chỉ report, không fix.

**Solution:** Tool mới:
```python
@mcp.tool()
def wiki_auto_fix(dry_run: bool = True) -> str:
    """
    Auto-fix common issues found by wiki_lint:
    - Broken wikilinks → replace với text (remove brackets)
    - Orphan pages → thêm vào _index.md với TODO comment
    - Missing frontmatter → tạo minimal frontmatter từ filename
    """
```

---

### P2.4 — `wiki_stats` — Dashboard nhanh

**Problem:** Không có cái nhìn tổng quan về vault health và progress.

**Solution:**
```python
@mcp.tool()
def wiki_stats() -> str:
    """
    Returns:
    - Total pages by tag
    - Recently updated (last 7 days)
    - Pages without updates (>30 days)
    - Orphan count, broken link count
    - Top linked pages
    """
```

---

## Priority 3 — Enhancement (Tốt nếu có)

### P3.1 — Scheduled Tasks (Windows Task Scheduler)

**Problem:** Không có scheduled maintenance.

**Solution:** Script `scripts/daily_maintenance.py`:
```python
# Chạy qua Windows Task Scheduler mỗi ngày
# 1. wiki_lint() → save report
# 2. wiki_rebuild_index()
# 3. Nếu lint score tệ → email/notification
```

**Setup:**
```powershell
# Tạo scheduled task
schtasks /create /tn "LLMWiki-Daily" /tr "python C:\...\scripts\daily_maintenance.py" /sc daily /st 08:00
```

---

### P3.2 — URL/PDF Ingestion

**Problem:** `wiki_ingest_raw` chỉ nhận text content.

**Solution:** Tool mới `wiki_ingest_url`:
```python
@mcp.tool()
def wiki_ingest_url(url: str, filename: str | None = None) -> str:
    """
    Fetch URL, extract text, save to raw/.
    Supports: HTML pages, PDF (basic text extraction)
    """
    import httpx
    from html2text import html2text  # pip install html2text
    
    r = httpx.get(url, follow_redirects=True)
    if "pdf" in r.headers.get("content-type", ""):
        # basic PDF extraction
        ...
    else:
        text = html2text(r.text)
    fname = filename or _url_to_filename(url)
    return wiki_ingest_raw(fname, text)
```

---

### P3.3 — `.obsidian/` Config với Plugins

**Problem:** Vault chưa có Obsidian app config → không tận dụng được Obsidian ecosystem.

**Solution:** Thêm template `.obsidian/` config:
```
vault/.obsidian/
├── app.json          # Obsidian settings
├── plugins/
│   └── dataview/     # Dataview: query wiki như database
└── community-plugins.json
```

**Recommended plugins:**
- **Dataview** — query pages theo tags, dates
- **Templater** — template cho tạo page mới
- **Graph View** — visualize wikilinks

---

### P3.4 — Export API

**Problem:** Không có cách export vault thành các format khác.

**Solution:**
```python
@mcp.tool()
def wiki_export(format: str = "json", tag: str = "") -> str:
    """
    Export vault content:
    - 'json': all pages as JSON array
    - 'obsidian': zip vault/wiki/ folder
    - 'markdown': concatenated markdown
    """
```

---

## Roadmap

```
Phase 1 — Foundation Fix (1-2 tuần)
  ├── P1.1: Seed vault với 10+ pages
  ├── P1.2: wiki_write_safe
  ├── P1.3: Cải thiện CLAUDE.md capture trigger
  └── P1.4: Thêm web search vào knowledge_search

Phase 2 — Core Enhancement (2-4 tuần)
  ├── P2.1: Semantic search (local embeddings)
  ├── P2.2: HTTP transport cho Claude.ai
  ├── P2.3: wiki_auto_fix
  └── P2.4: wiki_stats dashboard

Phase 3 — Polish (1-2 tháng)
  ├── P3.1: Scheduled maintenance
  ├── P3.2: URL/PDF ingestion
  ├── P3.3: Obsidian config + plugins
  └── P3.4: Export API
```

---

## Success Metrics

| Metric | AS-IS | TO-BE Target |
|--------|-------|-------------|
| Số pages trong vault | 0 | ≥50 pages sau 1 tháng |
| % conversation captured | ~0% | ≥70% |
| Search relevance | Keyword only | Semantic + keyword |
| Health check frequency | Manual | Daily automated |
| Claude.ai support | ❌ | ✅ (Phase 2) |
| Knowledge sources | Arxiv only | Arxiv + Web + Wikipedia |
| Wiki usability | Desktop only | Desktop + Web |
