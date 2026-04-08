# Master Checklist — LLM Wiki System Validation
> So sánh **Idea ban đầu** vs **Hệ thống hiện tại**
> Ngày audit: 2026-04-08

---

## Mục tiêu từ Idea.md

> *"Khi dùng Claude Desktop hoặc Claude.ai thì các knowledge trôi nổi trong đó sẽ được lưu vào kho kiến thức llm-wiki dưới dạng obsidian vault. Liên tục update, kiểm tra, chỉnh sửa để keep wiki này healthy. Dựa trên ý tưởng llm-wiki của Karpathy và các skills/MCP của Kepano liên quan tới Obsidian."*

---

## Checklist tổng quan

### A. Nền tảng (Foundation)

| # | Tiêu chí | Trạng thái | Ghi chú |
|---|----------|-----------|---------|
| A1 | Knowledge lưu dạng Obsidian vault (`.md` + frontmatter YAML) | ✅ Có | `vault/wiki/*.md` có YAML frontmatter |
| A2 | Vault có cấu trúc rõ ràng (`raw/`, `wiki/`, `papers/`, `log.md`) | ✅ Có | Đúng theo CLAUDE.md |
| A3 | Tích hợp với Claude Desktop qua MCP | ✅ Có | `mcp_server/server.py` + FastMCP |
| A4 | Hoạt động với Claude.ai (web) | ❌ Chưa | MCP chỉ chạy local stdio cho Desktop |
| A5 | Có thể dùng lại từ nhiều conversations | ⚠️ Một phần | Vault persistent nhưng không auto-sync với Claude.ai |

### B. Knowledge Capture (Lưu kiến thức)

| # | Tiêu chí | Trạng thái | Ghi chú |
|---|----------|-----------|---------|
| B1 | Tự động capture knowledge từ conversation | ⚠️ Một phần | Có workflow trong CLAUDE.md nhưng phụ thuộc agent tự nhận ra |
| B2 | Ingest raw source (article/paper/notes) | ✅ Có | `wiki_ingest_raw` tool |
| B3 | Phân tích và trích xuất concepts, entities | ⚠️ Một phần | Logic nằm trong prompt của CLAUDE.md, không có code tự động |
| B4 | Tránh duplicate khi tạo page mới | ✅ Có | Workflow yêu cầu `wiki_search` trước |
| B5 | Conflict detection giữa sources | ⚠️ Một phần | Chỉ là quy tắc trong prompt, không enforce tự động |
| B6 | Conversation capture tự động (không cần user yêu cầu) | ❌ Chưa | Phụ thuộc hoàn toàn vào agent, không có trigger/hook |

### C. Knowledge Synthesis (Tổng hợp)

| # | Tiêu chí | Trạng thái | Ghi chú |
|---|----------|-----------|---------|
| C1 | Merge thông tin từ nhiều source | ✅ Có | `wiki_update` với `mode=merge/append` |
| C2 | Wikilinks kết nối các trang với nhau | ✅ Có | Convention được define rõ |
| C3 | Tag taxonomy chuẩn | ✅ Có | Tags: source, concept, entity, strategy, log |
| C4 | Auto-generate index từ tất cả pages | ✅ Có | `wiki_rebuild_index` |
| C5 | Slug naming convention (kebab-case, prefix) | ✅ Có | Documented trong CLAUDE.md |

### D. Knowledge Health (Kiểm tra sức khỏe)

| # | Tiêu chí | Trạng thái | Ghi chú |
|---|----------|-----------|---------|
| D1 | Phát hiện broken wikilinks | ✅ Có | `wiki_lint` kiểm tra |
| D2 | Phát hiện orphan pages | ✅ Có | `wiki_lint` kiểm tra |
| D3 | Phát hiện missing frontmatter | ✅ Có | `wiki_lint` kiểm tra |
| D4 | Tự động fix health issues | ❌ Chưa | `wiki_lint` chỉ report, không fix |
| D5 | Định kỳ health check (schedule) | ❌ Chưa | Manual trigger only |
| D6 | Lint report lưu vào `_lint-report.md` | ✅ Có | Implemented |

### E. Research (Tìm kiếm tài liệu)

| # | Tiêu chí | Trạng thái | Ghi chú |
|---|----------|-----------|---------|
| E1 | Tìm kiếm papers trên Arxiv | ✅ Có | `arxiv_search` tool |
| E2 | Lưu paper metadata vào vault | ✅ Có | `arxiv_fetch_paper` → `vault/papers/` |
| E3 | Auto-search khi topic chưa có trong wiki | ⚠️ Một phần | `knowledge_search` có logic nhưng cần agent trigger |
| E4 | Search từ nguồn ngoài Arxiv (web, HF) | ❌ Chưa | `knowledge_search` chỉ dùng Arxiv API |
| E5 | Semantic search (vector/embedding) | ❌ Chưa | Chỉ có full-text search |

### F. Query (Truy vấn)

| # | Tiêu chí | Trạng thái | Ghi chú |
|---|----------|-----------|---------|
| F1 | Full-text search trong wiki | ✅ Có | `wiki_search` |
| F2 | Filter theo tag | ✅ Có | `wiki_list(tag=...)` |
| F3 | Trả lời với citations từ wiki pages | ✅ Có | Convention trong CLAUDE.md |
| F4 | Semantic/vector search | ❌ Chưa | Không có embedding |
| F5 | Insight mới từ query được lưu lại | ⚠️ Một phần | Quy tắc trong prompt, threshold >3 câu |

### G. Activity Tracking (Ghi lịch sử)

| # | Tiêu chí | Trạng thái | Ghi chú |
|---|----------|-----------|---------|
| G1 | Append-only activity log | ✅ Có | `vault/log.md` |
| G2 | Log mỗi lần create/update/delete | ✅ Có | `_append_log()` được gọi trong mọi tool |
| G3 | Session start checklist | ✅ Có | Documented trong CLAUDE.md |

---

## Tóm tắt điểm số

| Hạng mục | Đạt | Một phần | Chưa có | Tổng |
|---------|-----|----------|---------|------|
| A. Foundation | 3 | 1 | 1 | 5 |
| B. Knowledge Capture | 2 | 3 | 1 | 6 |
| C. Knowledge Synthesis | 5 | 0 | 0 | 5 |
| D. Knowledge Health | 4 | 0 | 2 | 6 |  
| E. Research | 2 | 1 | 2 | 5 |
| F. Query | 2 | 1 | 2 | 5 |
| G. Activity Tracking | 3 | 0 | 0 | 3 |
| **Tổng** | **21** | **6** | **8** | **35** |

**Score: 21/35 = 60% đạt + 6 partial = ~68% phủ mục tiêu**

---

## Kết luận nhanh

- ✅ **Core infrastructure** (MCP server, vault structure, basic tools) = tốt
- ⚠️ **Automation** (conversation capture, auto-trigger, auto-fix) = yếu — phụ thuộc vào agent prompt
- ❌ **Claude.ai web support** = chưa có
- ❌ **Semantic search** = chưa có
- ❌ **Multi-source research** (ngoài Arxiv) = chưa có

Xem chi tiết trong các file validation report riêng biệt.
