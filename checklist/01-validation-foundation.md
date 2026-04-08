# Validation Report 01 — Foundation & Integration
> Ngày audit: 2026-04-08 | Category: A (Foundation)

---

## Scope

Kiểm tra cơ sở hạ tầng: vault structure, MCP integration, Obsidian compatibility.

---

## Test Cases

### A1 — Vault dạng Obsidian (`.md` + YAML frontmatter)

**Expected (từ Idea):** Knowledge được lưu dạng Obsidian vault, có thể mở bằng Obsidian.

**Actual:**
- `vault/wiki/*.md` — có YAML frontmatter chuẩn (title, slug, tags, source, created, updated)
- Format tương thích với Obsidian (wikilinks `[[...]]`, tags, frontmatter)
- Chưa có `.obsidian/` config directory (Obsidian plugins, themes)

**Evidence:**
```python
# server.py line 70-82
def _build_page(slug, title, content, tags, source, created=None):
    meta = {"title": title, "slug": slug, "tags": tags, ...}
    fm = yaml.dump(meta, ...).strip()
    return f"---\n{fm}\n---\n\n{content.strip()}\n"
```

**Verdict:** ✅ **PASS** — Vault hoàn toàn tương thích Obsidian. Có thể mở `vault/` bằng Obsidian app.

---

### A2 — Cấu trúc vault rõ ràng

**Expected:** `raw/`, `wiki/`, `papers/`, `log.md`

**Actual:**
```
vault/
├── raw/          ✅ tồn tại (empty)
├── wiki/         ✅ tồn tại (_index.md, _lint-report.md)
├── papers/       ✅ tồn tại (empty)
└── log.md        ✅ tồn tại (1 entry từ 2026-04-08)
```

**Verdict:** ✅ **PASS** — Cấu trúc đúng 100%.

---

### A3 — Tích hợp Claude Desktop qua MCP

**Expected:** Claude Desktop có thể gọi wiki tools.

**Actual:**
- `mcp_server/server.py` dùng `FastMCP` từ `mcp[cli]>=1.6.0`
- Transport: `stdio` (phù hợp Claude Desktop)
- Config trong `claude_desktop_config.json` đã documented trong README.md
- 13 tools được expose: `wiki_*`, `arxiv_*`, `knowledge_search`

**Evidence:**
```python
# server.py line 600-601
if __name__ == "__main__":
    mcp.run(transport="stdio")
```

**Verdict:** ✅ **PASS** — Setup đúng chuẩn MCP stdio protocol.

---

### A4 — Hoạt động với Claude.ai (web)

**Expected (từ Idea):** *"Khi dùng Claude Desktop **hoặc Claude.ai**"*

**Actual:**
- MCP server dùng `stdio` transport → chỉ hoạt động với Claude Desktop
- Claude.ai web không hỗ trợ MCP stdio local server
- Không có HTTP/SSE transport fallback
- Không có hosted MCP option

**Verdict:** ❌ **FAIL** — Claude.ai web hoàn toàn không được support. Đây là gap quan trọng.

**Root cause:** MCP stdio chỉ chạy trên local machine với Claude Desktop. Claude.ai cần remote MCP endpoint (HTTP/SSE).

---

### A5 — Knowledge persistent và tái sử dụng được

**Expected:** Knowledge lưu lại, dùng được ở session sau.

**Actual:**
- Vault lưu trên filesystem → persistent ✅
- Mỗi session Claude Desktop có thể gọi `wiki_log`, `wiki_list` để xem lại ✅
- Không có sync mechanism giữa multiple Claude Desktop sessions ⚠️
- Vault path hardcoded theo máy tính của `nhata` ⚠️

**Verdict:** ⚠️ **PARTIAL** — Persistent nhưng không portable / multi-device.

---

## Summary

| Test | Verdict | Priority |
|------|---------|----------|
| A1 — Obsidian vault format | ✅ PASS | - |
| A2 — Vault structure | ✅ PASS | - |
| A3 — Claude Desktop MCP | ✅ PASS | - |
| A4 — Claude.ai web support | ❌ FAIL | HIGH |
| A5 — Persistence & reuse | ⚠️ PARTIAL | MEDIUM |

**Điểm: 3/5 full pass | 1 partial | 1 fail**
