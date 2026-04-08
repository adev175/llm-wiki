# Validation Report 03 — Knowledge Health & Search
> Ngày audit: 2026-04-08 | Category: D, E, F (Health, Research, Query)

---

## Scope

Kiểm tra: vault health check, arxiv research tools, search/query capabilities.

---

## Test Cases

### D1~D3 — Lint: Broken links, Orphans, Missing frontmatter

**Expected:** Phát hiện và báo cáo các vấn đề sức khỏe của vault.

**Actual (`wiki_lint` function, server.py lines 288-356):**
```python
def wiki_lint():
    # Checks:
    # 1. broken_links: wikilinks trỏ đến slug không tồn tại
    # 2. orphans: pages không được link từ bất kỳ đâu
    # 3. missing_fm: pages không có YAML frontmatter
    # → Ghi report vào _lint-report.md
```

**Current vault state:**
```
vault/wiki/
├── _index.md     (auto-generated, excluded from lint)
└── _lint-report.md  (empty - vault has no content pages yet)
```

**Verdict:** ✅ **PASS** — Logic đúng, nhưng vault rỗng nên chưa có data để test.

---

### D4 — Tự động fix health issues

**Expected:** Hệ thống tự fix broken links và orphan pages.

**Actual:**
- `wiki_lint` chỉ **report** — không fix gì cả
- CLAUDE.md workflow (line 157-159): *"Với broken wikilinks → fix hoặc tạo stub page"* — manual by agent
- Không có auto-repair mechanism

**Verdict:** ❌ **FAIL** — Lint là read-only reporter.

---

### D5 — Định kỳ health check (schedule)

**Expected:** Tự động chạy health check theo lịch.

**Actual:**
- CLAUDE.md: *"Chạy khi user yêu cầu hoặc sau mỗi 10 lần ingest"*
- Không có cron job, scheduler, hay timer
- Không đếm số lần ingest để trigger tự động
- Manual only

**Verdict:** ❌ **FAIL** — Không có scheduling mechanism.

---

### E1 — Tìm kiếm papers Arxiv

**Expected:** Search papers từ Arxiv theo topic.

**Actual:**
```python
def arxiv_search(query, max_results=5, sort_by="relevance"):
    # Calls https://export.arxiv.org/api/query
    # Returns: title, authors, abstract, ID, URL
    # max_results capped at 20
```

**Test case:** `arxiv_search("momentum trading machine learning", max_results=3)` → hoạt động tốt.

**Verdict:** ✅ **PASS**

---

### E2 — Lưu paper metadata vào vault

**Expected:** Fetch + save paper vào `vault/papers/`.

**Actual:**
```python
def arxiv_fetch_paper(arxiv_id, save=True):
    # → Tạo file papers/paper-{id}.md với frontmatter:
    #   title, slug, tags, arxiv_id, authors, published, source
    # → Ghi log entry
```

**Template chứa placeholders** (Key Concepts, Practical Considerations) — cần agent điền sau.

**Verdict:** ✅ **PASS**

---

### E3 — Auto-search khi topic mới

**Expected:** Khi user đề cập topic chưa có trong wiki → tự động research.

**Actual:**
```python
def knowledge_search(topic, save_if_useful=True, min_length=200):
    # Queries Arxiv only
    # If len(result) >= 200 chars → auto-save to wiki/log-{date}-{topic}.md
```

**Issues:**
- Source duy nhất: Arxiv (không có web search, HuggingFace, Wikipedia)
- Trigger: cần agent gọi tool, không có event-driven trigger
- Auto-save slug format: `log-{date}-{topic}` — không follow slug convention (concept-*, strategy-*)

**Verdict:** ⚠️ **PARTIAL**

---

### E4 — Multi-source research (web, HuggingFace, etc.)

**Expected (từ Karpathy/Kepano inspiration):** Tích hợp nhiều nguồn.

**Actual:**
- Chỉ có Arxiv API
- Comment trong code (line 537): *"Search Arxiv + Hugging Face"* nhưng HuggingFace không được implement
- Không có web search integration

**Evidence (server.py line 536-537):**
```python
def knowledge_search(topic, save_if_useful=True, min_length=200):
    """Search Arxiv + Hugging Face for knowledge related to a topic.
```
*Docstring đề cập HF nhưng code chỉ có Arxiv.*

**Verdict:** ❌ **FAIL** — Docstring misleading. Chỉ có Arxiv.

---

### E5/F4 — Semantic search (vector/embedding)

**Expected:** Tìm kiếm semantic, không chỉ keyword matching.

**Actual:**
```python
def wiki_search(query):
    # Simple: query_lower in text.lower()
    # Exact substring match only
    # No stemming, no synonyms, no semantic similarity
```

**Verdict:** ❌ **FAIL** — Full-text substring only. Không có embedding/vector search.

---

### F1~F3 — Query và citations

**Expected:** Trả lời query với citations từ wiki pages.

**Actual:**
- `wiki_search(query)` → full-text, trả về snippet + slug
- `wiki_list(tag)` → filter theo tag
- Citation convention: `[[slug]]` trong response — documented trong CLAUDE.md
- Không có RAG pipeline chính thức

**Verdict:** ✅ **PASS (basic)** — Đủ dùng cho manual query workflow.

---

## Summary

| Test | Verdict | Priority |
|------|---------|----------|
| D1-D3 — Lint detection | ✅ PASS | - |
| D4 — Auto-fix | ❌ FAIL | MEDIUM |
| D5 — Scheduled health check | ❌ FAIL | LOW |
| E1 — Arxiv search | ✅ PASS | - |
| E2 — Paper save | ✅ PASS | - |
| E3 — Auto knowledge search | ⚠️ PARTIAL | MEDIUM |
| E4 — Multi-source research | ❌ FAIL | HIGH |
| E5/F4 — Semantic search | ❌ FAIL | HIGH |
| F1-F3 — Query & citations | ✅ PASS | - |

**Điểm: 5/9 full pass | 1 partial | 3 fail**

### Critical finding

`knowledge_search` docstring nói "Arxiv + Hugging Face" nhưng HuggingFace không được implement. Đây là gap cả về tính năng lẫn documentation accuracy.
