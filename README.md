# LLM Wiki

Obsidian vault + MCP server de bien Claude Desktop thanh mot **knowledge compiler** tu dong.

## Setup nhanh

### 1. Cai dependencies
```bash
pip install -r mcp_server/requirements.txt
```

### 2. Cau hinh Claude Desktop

Mo file: `%APPDATA%\Claude\claude_desktop_config.json`

Them vao:
```json
{
  "mcpServers": {
    "llm-wiki": {
      "command": "python",
      "args": ["C:\Users\nhata\PycharmProjects\llm-wiki\mcp_server\server.py"]
    }
  }
}
```

### 3. Restart Claude Desktop hoan toan

---

## Tools co san sau khi setup

| Tool | Chuc nang |
|------|-----------|
| wiki_write | Tao page moi |
| wiki_update | Cap nhat page cu |
| wiki_read | Doc page |
| wiki_search | Tim kiem full-text |
| wiki_list | Liet ke tat ca pages |
| wiki_rebuild_index | Tai tao index |
| wiki_lint | Health check |
| wiki_log | Xem lich su |
| arxiv_search | Tim papers tren Arxiv |
| arxiv_fetch_paper | Lay paper + luu vao vault/papers/ |
| knowledge_search | Auto-search + validate + luu wiki |

## Vault Structure

```
vault/
├── raw/          # Immutable raw sources
├── wiki/         # Knowledge pages (Claude owns)
├── papers/       # Arxiv papers
└── log.md        # Activity log
```

Xem CLAUDE.md de biet day du conventions va workflows.
