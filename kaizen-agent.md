# Kaizen Agent — Quy trình tìm lỗi & cải tiến hệ thống

> **Mục tiêu:** Agent dùng file này như một quy trình chuẩn (Standard Work) để quan sát hệ thống, phát hiện điểm bất thường, ghi nhận có cấu trúc, và từ đó sinh ra idea cải tiến. Không phải sửa ngay — mà là *nhìn thấy rõ trước, hành động sau*.

---

## Vault Structure (tích hợp vào LLM Wiki)

```
vault/
├── raw/                             # Nguồn: logs, code, transcripts, reports
├── 10-kaizen/                       # Kaizen files (type: kaizen)
│   ├── kaizen-backlog.md            # Danh sách issue + idea — LIVING DOCUMENT
│   ├── kaizen-standard.md           # Chuẩn hiện tại của hệ thống (baseline)
│   └── kaizen-log-<date>.md         # Mỗi vòng PDCA = 1 log entry
├── _index.md                        # vault root — auto-gen
├── _lint-report.md                  # vault root — auto-gen
└── log.md
```

**Quy tắc cứng:**
- `kaizen-backlog.md` là file duy nhất được **append liên tục** — không xoá entry cũ, chỉ thêm trạng thái.
- `kaizen-standard.md` là baseline — chỉ update sau khi bước **A (Act)** hoàn thành và được xác nhận.
- Mỗi issue phải có `id` duy nhất theo format `K-<YYYY-MM-DD>-<seq>` (e.g. `K-2026-04-11-003`).
- Tất cả kaizen files dùng `type: kaizen` trong frontmatter → tự động route vào `10-kaizen/`.

---

## Nguyên tắc nền (Tư duy Kaizen)

Agent phải internalize 6 nguyên tắc này trước khi bắt đầu bất kỳ workflow nào:

| # | Nguyên tắc | Ý nghĩa hành động |
|---|-----------|-------------------|
| 1 | **Genchi Genbutsu** (現地現物) | Đọc trực tiếp source — log, code, data, transcript. Không phán đoán từ xa. |
| 2 | **5 Whys** | Khi thấy lỗi, hỏi "Tại sao?" ít nhất 3–5 lần để tìm root cause, không chỉ symptom. |
| 3 | **Mura / Muri / Muda** | Tìm: bất nhất (inconsistency), quá tải (overload), lãng phí (waste). |
| 4 | **PDCA** | Mọi cải tiến phải có chu trình: Plan → Do (nhỏ) → Check (đo) → Act (chuẩn hóa). |
| 5 | **標準化** | Chuẩn hóa trước, tối ưu sau. Nếu chưa có chuẩn, lỗi không nhìn thấy được. |
| 6 | **見える化** | Bất thường phải nhìn thấy ngay — không đợi báo cáo. |

---

## Workflow chính: OBSERVE → CLASSIFY → PDCA → FILE

### Bước 0 — Nạp baseline

```
1. wiki_read("kaizen-standard") → nắm chuẩn hiện tại của hệ thống
2. wiki_read("kaizen-backlog") → xem issue nào đang open / in-progress
3. wiki_log(lines=5) → xem gần nhất làm gì
4. Nếu chưa có kaizen-standard.md → tạo ngay từ những gì biết về hệ thống
```

Nếu `kaizen-standard.md` chưa tồn tại, tạo với template:

```markdown
# System Standard (Baseline)

## Mô tả hệ thống
[Hệ thống này làm gì, dùng ở đâu, ai dùng]

## Các component chính
- Component A: [chức năng, đầu vào, đầu ra]
- Component B: ...

## KPI / Metrics chuẩn
- [Metric 1]: [giá trị mong đợi]
- [Metric 2]: ...

## Known constraints
- [Giới hạn đã biết và đã chấp nhận]

**Version:** 1.0 | **Ngày tạo:** <date> | **Nguồn:** conversation / document
```

---

### Bước 1 — OBSERVE (Genchi Genbutsu)

Khi nhận được source mới (log, code, transcript, report):

```
1. wiki_ingest_raw(filename, content) → lưu raw
2. Đọc toàn bộ source — không filter trước
3. Với mỗi đoạn đọc, tự hỏi 3 câu:
   a. "Cái này có khớp với kaizen-standard không?" → nếu không → FLAG
   b. "Cái này có lặp lại pattern đã thấy không?" → nếu có → LINK tới issue cũ
   c. "Cái này gây ra gì downstream?" → trace nguyên nhân
```

**Các dấu hiệu cần flag ngay (Andon triggers):**

| Dấu hiệu | Loại | Ví dụ |
|----------|------|-------|
| Output không nhất quán với input tương tự | Mura | Cùng query → kết quả khác nhau |
| Bước xử lý lặp lại không cần thiết | Muda | Fetch cùng data 3 lần |
| Hệ thống phụ thuộc ngầm chưa documented | Missing standard | Module A dùng format của B nhưng không ai ghi |
| Error bị catch nhưng không log | Blind spot | `except: pass` không có trace |
| Metric vượt ngưỡng hoặc trend xấu | KPI deviation | Latency tăng 3 ngày liên tiếp |
| User workaround ("tôi phải làm thêm bước này") | Poka-yoke gap | Phải thêm bước thủ công để tránh lỗi |
| Assumption không được kiểm tra | Theoretical only | "Tôi nghĩ là nó hoạt động" |

---

### Bước 2 — CLASSIFY (5 Whys + Root Cause)

Với mỗi issue được flag, chạy quy trình phân tích:

```
1. Viết symptom rõ ràng (1 câu, có thể đo được)
2. Hỏi "Tại sao?" ít nhất 3 lần:
   - Why 1: [symptom → cause level 1]
   - Why 2: [cause 1 → cause level 2]
   - Why 3: [cause 2 → root cause hypothesis]
3. Phân loại root cause:
   - [PROCESS] → quy trình thiếu / sai
   - [STANDARD] → chưa có chuẩn / chuẩn sai
   - [DESIGN] → thiết kế có gap logic
   - [DATA] → dữ liệu không đủ / sai format
   - [VISIBILITY] → lỗi xảy ra nhưng không ai thấy
4. Đánh giá: empirical (đã thấy xảy ra) vs theoretical (có thể xảy ra)
```

**Ví dụ phân tích:**
```
Symptom: Wiki agent tạo duplicate page về cùng một concept.
Why 1: Agent không search trước khi wiki_write.
Why 2: Workflow trong CLAUDE.md không enforce bước search.
Why 3: Không có poka-yoke ngăn wiki_write khi chưa search.
Root cause: [PROCESS] Missing mandatory pre-check step.
Type: empirical (đã xảy ra)
```

---

### Bước 3 — FILE vào kaizen-backlog.md

Mỗi issue được thêm vào `kaizen-backlog.md` theo format chuẩn:

```markdown
## K-<YYYY-MM-DD>-<seq> | <title ngắn gọn>

**Status:** `open` | `in-progress` | `done` | `wont-fix`
**Loại:** `PROCESS` | `STANDARD` | `DESIGN` | `DATA` | `VISIBILITY`
**Nguồn:** [[source-<slug>]] | conversation-<date>
**Phát hiện:** <date>

### Symptom
[Mô tả rõ, có thể quan sát, có thể đo]

### 5 Whys
- Why 1: ...
- Why 2: ...
- Why 3: ... → **Root cause: [loại] — [mô tả]**

### Impact
- **Mức độ:** `critical` | `high` | `medium` | `low`
- **Ai/cái gì bị ảnh hưởng:** ...
- **Tần suất:** `always` | `sometimes` | `rare` | `unknown`

### Idea cải tiến (PDCA — Plan)
> Phần này sinh ra *hypothesis*, không phải quyết định cuối.

- **Idea 1:** [mô tả thay đổi nhỏ có thể thử]
  - Effort: `low` | `medium` | `high`
  - Expected outcome: [KPI nào sẽ thay đổi, theo hướng nào]
  - Test scope: [thử ở đâu, với bao nhiêu case]

- **Idea 2:** [alternative approach nếu có]
  ...

### PDCA Cycle (điền khi thực hiện)
- **D (Do):** [thay đổi đã làm, phạm vi nhỏ]
- **C (Check):** [đo trước/sau — KPI thực tế]
- **A (Act):** [ ] Chuẩn hóa vào kaizen-standard.md | [ ] Adjust và lặp | [ ] Abandon

### Notes
[Các quan sát phụ, liên quan tới issue khác]
**Liên kết:** [[K-...]] [[concept-...]]
```

---

### Bước 4 — GENERATE IDEAS (Cải tiến từ pattern)

Sau khi có ≥3 issue cùng loại, agent chạy **pattern synthesis**:

```
1. wiki_search("kaizen") → đọc tất cả issue open
2. Group theo root cause type (PROCESS / STANDARD / DESIGN / DATA / VISIBILITY)
3. Với mỗi cluster ≥3 issue:
   → Đây là systemic gap, không phải individual bug
   → Sinh ra 1 "Feature Idea" page riêng
4. wiki_write("kaizen-idea-<topic>", ...)
```

**Template Feature Idea page:**

```markdown
# Feature Idea: <tên>

**Sinh ra từ:** [[K-...]], [[K-...]], [[K-...]]
**Loại systemic gap:** [PROCESS / STANDARD / DESIGN / DATA / VISIBILITY]
**Ngày:** <date>

## Vấn đề gốc (pattern)
[Mô tả pattern chung từ các issue]

## Proposed feature / improvement
[Mô tả tính năng hoặc thay đổi hệ thống]

## PDCA Plan
- **Plan:** [hypothesis — nếu làm X thì Y sẽ cải thiện]
- **Do:** [thử nhỏ nhất có thể validate hypothesis này]
- **Check KPI:** [đo cái gì, so với baseline nào]
- **Act:** [nếu validate → standard hóa vào đâu]

## Poka-yoke angle
[Có thể thiết kế để lỗi này *không thể xảy ra* không?]

## Liên kết
[[kaizen-standard]] [[kaizen-backlog]] [[concept-...]]
```

---

### Bước 5 — LINT định kỳ (見える化 — Visual Health Check)

Chạy sau mỗi 5 issue mới hoặc khi user yêu cầu:

```
1. wiki_lint() → check broken links, orphans
2. Đọc kaizen-backlog.md → đếm:
   - open issues theo loại
   - issues "in-progress" quá 14 ngày không update → flag stale
   - issues "done" nhưng chưa update kaizen-standard → flag gap
3. Tạo visual summary trong _lint-report.md:
```

```markdown
## Kaizen Health — <date>

| Loại | Open | In-Progress | Done | Wont-Fix |
|------|------|-------------|------|----------|
| PROCESS | 3 | 1 | 2 | 0 |
| STANDARD | 1 | 0 | 4 | 1 |
| DESIGN | 2 | 2 | 0 | 0 |
| DATA | 0 | 1 | 1 | 0 |
| VISIBILITY | 4 | 0 | 1 | 0 |

### ⚠ Cần chú ý
- [K-xxx]: in-progress >14 ngày, chưa có C/A step
- [K-yyy]: done nhưng chưa chuẩn hóa vào kaizen-standard

### 📊 Top systemic gap
VISIBILITY (4 open) → có thể là 1 systemic issue chưa được address
```

---

## Anti-patterns — KHÔNG làm

- ❌ **Sửa ngay khi thấy lỗi** — phải file trước, PDCA sau. Sửa vội = bỏ qua root cause.
- ❌ **Why chỉ 1 lần** — "vì lỗi code" không phải root cause. Đào sâu hơn.
- ❌ **Issue không có KPI** — nếu không đo được trước/sau, không biết có cải thiện không.
- ❌ **Update kaizen-standard trước bước A** — standard chỉ update sau khi đã validate.
- ❌ **Idea quá lớn** — mỗi PDCA cycle phải có scope nhỏ đủ để test trong 1–3 ngày.
- ❌ **Bỏ qua Poka-yoke angle** — luôn hỏi: "có thiết kế được để lỗi này không thể xảy ra không?"

---

## Session Start Checklist

```
1. wiki_read("kaizen-standard")    → nắm baseline hiện tại
2. wiki_read("kaizen-backlog")     → xem gì đang open
3. wiki_lint()                     → nhìn health tổng thể
4. Hỏi user: "Có source mới để observe không, hay muốn review issue đang open?"
```

---

## Tích hợp với CLAUDE.md chính

Thêm vào section **Workflows** trong `CLAUDE.md`:

```markdown
### 5. KAIZEN — Tìm lỗi và cải tiến hệ thống

Khi user paste log / code / report / transcript để review:

1. Chạy OBSERVE → CLASSIFY → FILE như trong `kaizen-agent.md`
2. Mỗi issue → 1 entry trong `kaizen-backlog.md`
3. Sau ≥3 issue cùng loại → tổng hợp thành Feature Idea page
4. Sau mỗi 5 issue → chạy lint và report health summary
```