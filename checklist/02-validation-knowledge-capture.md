# Validation Report 02 — Knowledge Capture
> Ngày audit: 2026-04-08 | Category: B (Knowledge Capture)

---

## Scope

Kiểm tra khả năng hệ thống thu thập và lưu trữ kiến thức từ conversations và raw sources.

---

## Test Cases

### B1 — Tự động capture knowledge từ conversation

**Expected (từ Idea):** Knowledge "trôi nổi" trong conversation được tự động lưu vào vault.

**Actual:**
- Logic capture được document trong CLAUDE.md (`### 3. CONVERSATION CAPTURE`)
- Threshold: nếu answer >3 câu và có thể tái dùng → file it
- **Không có mechanism tự động**: hoàn toàn phụ thuộc agent tự nhận ra
- Không có hook/trigger sau mỗi conversation turn
- Không có post-processing pipeline

**Evidence (CLAUDE.md lines 108-119):**
```
Đây là điểm mấu chốt: sau mỗi đoạn conversation có insight, không cần user yêu cầu:
1. Identify: conversation này có insight gì đáng lưu không?
2. wiki_write hoặc wiki_update với source="conversation-<YYYY-MM-DD>"
3. Không cần thông báo trừ khi user hỏi
```

**Gap:** Đây là **prompt instruction**, không phải **code logic**. Agent có thể bỏ qua.

**Verdict:** ⚠️ **PARTIAL** — Về lý thuyết có; về thực tế không được enforce.

---

### B2 — Ingest raw source

**Expected:** Có thể lưu raw content (article, notes, PDF) vào vault.

**Actual:**
- `wiki_ingest_raw(filename, content)` → lưu vào `vault/raw/`
- Immutable: file đã tồn tại sẽ không bị overwrite (trả về error)
- Chỉ nhận text content (không parse PDF, HTML, URL)

**Evidence:**
```python
# server.py line 232-244
def wiki_ingest_raw(filename: str, content: str) -> str:
    path = RAW_DIR / filename
    if path.exists():
        return f"✗ Already exists: raw/{filename} — raw/ is immutable."
    path.write_text(content, encoding="utf-8")
```

**Limitation:** Không có URL fetcher, không có PDF parser.

**Verdict:** ✅ **PASS (basic)** — Text ingest hoạt động; nhưng thiếu URL/PDF ingestion.

---

### B3 — Phân tích và trích xuất concepts/entities

**Expected:** Sau khi ingest raw → auto-extract concepts, entities, strategies.

**Actual:**
- Logic extraction được describe trong CLAUDE.md workflow (INGEST step 3)
- **Implement bằng LLM reasoning** (agent đọc và phân tích), không phải NLP code
- Không có NER, không có entity extraction library
- Chất lượng extraction phụ thuộc vào model capability

**Verdict:** ⚠️ **PARTIAL** — Hoạt động nhờ LLM, nhưng không deterministic và không verifiable.

---

### B4 — Tránh duplicate khi tạo page mới

**Expected:** Kiểm tra tồn tại trước khi tạo page mới.

**Actual:**
- CLAUDE.md workflow: bước đầu tiên luôn là `wiki_search(query)`
- Anti-patterns section: `❌ Chạy wiki_write mà không wiki_search trước`
- `wiki_write` **overwrite mà không cảnh báo** nếu slug đã tồn tại (note: "Overwrites if slug already exists")

**Evidence:**
```python
# server.py line 98-115
def wiki_write(slug, title, content, tags=None, source="manual"):
    """Create a new wiki page. Overwrites if slug already exists."""
    path = WIKI_DIR / f"{slug}.md"
    existed = path.exists()
    page = _build_page(slug, title, content, tags or [], source)
    path.write_text(page, encoding="utf-8")
    action = "Updated" if existed else "Created"
```

**Gap:** Không có "create-only" mode hoặc confirmation khi overwrite existing page.

**Verdict:** ✅ **PASS (by convention)** — Phụ thuộc vào agent tuân thủ workflow.

---

### B5 — Conflict detection giữa sources

**Expected:** Khi source mới mâu thuẫn với nội dung cũ → flag rõ.

**Actual:**
- Convention documented (CLAUDE.md line 88-90):
  ```markdown
  > ⚠ **Conflict** (source: [[source-xyz]]): [claim A] contradicts [claim B] above.
  ```
- Không có automated conflict detection
- Hoàn toàn phụ thuộc agent tự nhận ra mâu thuẫn

**Verdict:** ⚠️ **PARTIAL** — Convention tốt, nhưng không được enforce bởi code.

---

### B6 — Auto conversation capture không cần user yêu cầu

**Expected:** Background capture sau mỗi conversation có insight.

**Actual:**
- Không có background job
- Không có conversation hook
- Không có session-end processing
- User phải explicitly trigger hoặc agent phải chủ động (không đảm bảo)

**Vault evidence:** `log.md` chỉ có 1 entry (initialization). Không có captured conversations.

**Verdict:** ❌ **FAIL** — Vault rỗng sau initialization = auto-capture không hoạt động trong thực tế.

---

## Summary

| Test | Verdict | Priority |
|------|---------|----------|
| B1 — Auto capture from conversation | ⚠️ PARTIAL | HIGH |
| B2 — Ingest raw source | ✅ PASS | - |
| B3 — Extract concepts/entities | ⚠️ PARTIAL | MEDIUM |
| B4 — Duplicate prevention | ✅ PASS | - |
| B5 — Conflict detection | ⚠️ PARTIAL | MEDIUM |
| B6 — Auto conversation capture | ❌ FAIL | CRITICAL |

**Điểm: 2/6 full pass | 3 partial | 1 fail**

### Root Cause

Hầu hết "automation" là **prompt engineering**, không phải **code automation**. Vault rỗng sau khi khởi tạo chứng minh rằng in practice, agent không tự động capture.
