Đúng phần lớn, nhưng không hoàn toàn "toàn bộ wiki". Flow thực tế là:

## Cách hoạt động (không RAG)

```
User hỏi → Claude suy nghĩ → Gọi MCP tool → Nhận kết quả → Trả lời
```

Cụ thể hơn, Claude có **3 cách lấy dữ liệu** từ wiki qua MCP:

| Tool | Cách hoạt động | Trả về |
|------|----------------|--------|
| `wiki_search(query)` | Grep case-insensitive toàn bộ file | Chỉ các page **match keyword** + snippet |
| `wiki_list(tag)` | List danh sách page (lọc theo tag) | Tiêu đề + slug (không có nội dung) |
| `wiki_read(slug)` | Đọc 1 page cụ thể | Toàn bộ nội dung page đó |

### So sánh với RAG

| | RAG | Hệ thống của bạn (MCP) |
|---|---|---|
| **Tìm kiếm** | Vector similarity (semantic) | Keyword grep (exact match) |
| **Cần** | Embedding model + Vector DB | Không gì cả, chỉ file system |
| **Ưu điểm** | Tìm được khái niệm liên quan | Đơn giản, không dependency |
| **Nhược điểm** | Phức tạp, cần maintain | Không tìm được synonyms/liên quan |

### Ví dụ thực tế

Khi bạn hỏi Claude: *"Momentum trading là gì?"*

1. Claude gọi `wiki_search("momentum trading")` → nhận danh sách page match
2. Claude gọi `wiki_read("concept-momentum-trading")` → đọc nội dung chi tiết
3. Claude tổng hợp và trả lời

**Không phải pass toàn bộ wiki** → chỉ pass những page liên quan thôi. Nhưng điểm yếu là nếu bạn tìm "đà tăng giá" thì sẽ **không match** được `momentum trading` vì chỉ là grep text, không có semantic understanding.

Nếu wiki nhỏ (< vài trăm pages) thì cách này hoàn toàn OK. Lúc nào wiki lớn lên hoặc cần tìm kiếm semantic thì mới cần thêm RAG.