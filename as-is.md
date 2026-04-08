# AS-IS — Hệ thống hiện tại (sau audit 2026-04-08)

> Phân tích và mô tả trạng thái thực tế của llm-wiki sau khi audit toàn bộ codebase.

---

## 1. Tổng quan kiến trúc

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Desktop (UI)                       │
│                  (Claude.ai web: KHÔNG hỗ trợ)             │
└─────────────────────┬───────────────────────────────────────┘
                      │ MCP stdio protocol
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              mcp_server/server.py (FastMCP)                 │
│                                                             │
│  Wiki Tools:          Arxiv Tools:      Knowledge:          │
│  wiki_write           arxiv_search      knowledge_search    │
│  wiki_update          arxiv_fetch_paper                     │
│  wiki_read                                                  │
│  wiki_delete                                                │
│  wiki_list                                                  │
│  wiki_search (ft)                                          │
│  wiki_ingest_raw                                           │
│  wiki_rebuild_index                                        │
│  wiki_lint                                                 │
│  wiki_log                                                  │
└─────────────────────┬───────────────────────────────────────┘
                      │ filesystem I/O
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                vault/ (Obsidian-compatible)                 │
│  raw/          wiki/           papers/      log.md          │
│  (rỗng)        _index.md       (rỗng)       (1 entry)       │
│                _lint-report.md                              │
│                (0 content pages)                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Thành phần chi tiết

### 2.1 MCP Server (`mcp_server/server.py`)

- **Framework:** `FastMCP` từ `mcp[cli]>=1.6.0`
- **Transport:** `stdio` — Local only, Claude Desktop only
- **Ngôn ngữ:** Python 3.x
- **Dependencies:** `httpx`, `PyYAML`, `python-dateutil`
- **Số tools:** 13 tools

| Tool | Mô tả | Trạng thái |
|------|-------|-----------|
| `wiki_write` | Tạo/overwrite page | ✅ Hoạt động |
| `wiki_update` | Append/merge vào page | ✅ Hoạt động |
| `wiki_read` | Đọc page theo slug | ✅ Hoạt động |
| `wiki_delete` | Xóa page | ✅ Hoạt động |
| `wiki_list` | Liệt kê pages (filter tag) | ✅ Hoạt động |
| `wiki_search` | Full-text search (substring) | ✅ Hoạt động (không semantic) |
| `wiki_ingest_raw` | Lưu raw source | ✅ Hoạt động (text only) |
| `wiki_rebuild_index` | Tạo lại `_index.md` | ✅ Hoạt động |
| `wiki_lint` | Health check report | ✅ Hoạt động (report only) |
| `wiki_log` | Đọc activity log | ✅ Hoạt động |
| `arxiv_search` | Tìm papers Arxiv | ✅ Hoạt động |
| `arxiv_fetch_paper` | Fetch + save paper | ✅ Hoạt động |
| `knowledge_search` | Auto-search + save | ⚠️ Arxiv only (docstring sai: nói "HF") |

### 2.2 Vault Structure

```
vault/
├── raw/               # Empty — chưa có source nào được ingest
├── wiki/
│   ├── _index.md      # Auto-gen (0 pages)
│   └── _lint-report.md # Empty
├── papers/            # Empty — chưa fetch paper nào
└── log.md             # 1 entry (initialization, 2026-04-08)
```

**Nhận xét:** Vault đang ở trạng thái **bootstrap** — cấu trúc đúng nhưng chưa có content.

### 2.3 Agent Instructions (`CLAUDE.md`)

- **Role:** "Wiki Compiler Agent"
- **Domain:** Quant trading / algorithmic trading research
- **Workflows được define:** INGEST, QUERY, CONVERSATION CAPTURE, ARXIV RESEARCH, KNOWLEDGE AUTO-SEARCH, LINT
- **Convention:** Slug naming, frontmatter schema, wikilink format
- **Anti-patterns:** 6 patterns được liệt kê rõ

**Vấn đề:** CLAUDE.md là **prompt engineering** — tất cả "automation" phụ thuộc vào LLM tuân thủ instructions.

---

## 3. Luồng dữ liệu thực tế

```
User (trong Claude Desktop)
    │
    │ gõ text / paste content
    ▼
Claude Agent
    │ đọc CLAUDE.md → biết cần làm gì
    │
    ├─ IF "có insight/content" → gọi wiki_write / wiki_update
    ├─ IF "user hỏi" → wiki_search → wiki_read → trả lời
    ├─ IF "topic mới" → knowledge_search (Arxiv)
    └─ IF "user muốn paper" → arxiv_search → arxiv_fetch_paper
    │
    ▼
vault/ (filesystem)
```

**Vấn đề luồng:**
- Bước "IF có insight" là **điều kiện không deterministic** — agent có thể quyết định khác nhau
- Không có guaranteed pipeline
- Vault rỗng sau khởi tạo = evidence rằng pipeline chưa được test end-to-end

---

## 4. Điểm mạnh hiện tại

| Điểm mạnh | Chi tiết |
|-----------|---------|
| **Vault format chuẩn** | Hoàn toàn compatible với Obsidian app |
| **MCP integration clean** | 13 tools, đúng chuẩn FastMCP |
| **Arxiv integration** | Fetch papers real-time, save có metadata |
| **Activity log** | Append-only, trace được mọi thay đổi |
| **CLAUDE.md chi tiết** | Workflows, conventions, anti-patterns được document tốt |
| **Health check** | `wiki_lint` phát hiện broken links, orphans, missing frontmatter |

---

## 5. Điểm yếu hiện tại

| Điểm yếu | Severity | Chi tiết |
|----------|---------|---------|
| **Vault rỗng** | HIGH | Chưa có 1 page nào được tạo — hệ thống chưa được vận hành |
| **Auto-capture = 0** | CRITICAL | Conversation capture phụ thuộc agent, không được enforce |
| **Claude.ai web = không hỗ trợ** | HIGH | MCP stdio chỉ cho Desktop |
| **Search = keyword only** | HIGH | Không có semantic/vector search |
| **Multi-source = chỉ Arxiv** | MEDIUM | knowledge_search thiếu web search, HuggingFace |
| **wiki_write overwrite silent** | MEDIUM | Không có write-protection hay confirmation |
| **Không có scheduled tasks** | LOW | Lint, index rebuild phải manual |
| **Path hardcoded** | LOW | `nhata/PycharmProjects/` — không portable |

---

## 6. Gap so với Idea ban đầu

| Idea goal | AS-IS |
|-----------|-------|
| Claude Desktop ✓, Claude.ai ✗ | Claude Desktop only |
| Knowledge "trôi nổi" được lưu | Chỉ khi agent chủ động — không guaranteed |
| "Liên tục update" | Không có automation loop |
| "Kiểm tra healthy" | Có lint tool, không có scheduled check |
| Dựa trên Karpathy llm-wiki | Concept đúng, implementation cơ bản |
| Dựa trên Kepano Obsidian MCP | Vault format đúng; Kepano tools chưa được integrate |

---

## 7. Đánh giá tổng thể

- **Score:** 60% mục tiêu được implement (21/35 criteria pass)
- **Trạng thái:** Early prototype — infrastructure đúng, automation chưa có
- **Biggest gap:** Vault rỗng sau khởi tạo = hệ thống chưa thực sự "sống"
- **Next step critical:** Cần ít nhất 1 conversation captured để validate end-to-end flow
