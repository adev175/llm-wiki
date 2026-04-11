# LLM Wiki

An Obsidian vault + MCP server that turns Claude into a **personal knowledge compiler** — it reads your research, extracts concepts, links ideas together, and answers questions from what it has learned.

---

## Install

```bash
pip install -r mcp_server/requirements.txt
```

Add to `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "llm-wiki": {
      "command": "python",
      "args": ["C:\\Users\\nhata\\PycharmProjects\\llm-wiki\\mcp_server\\server.py"]
    }
  }
}
```

Restart Claude Desktop. Done.

---

## How to use

Just talk to Claude naturally:

- **"Here's an article about momentum trading — add it to the wiki"** → Claude extracts concepts, creates/updates pages, links related ideas
- **"What do we know about mean reversion?"** → Claude searches the wiki and answers with citations
- **"Find papers on reinforcement learning for trading"** → Claude searches Arxiv, fetches relevant papers, saves them

Everything gets saved automatically. You don't need to learn any commands.

---

## Features

### Knowledge pages

Each topic gets its own Markdown file in `vault/wiki/` with structured frontmatter. Pages are linked with `[[wikilinks]]` so nothing is an island. Claude never creates a page without first checking if one already exists.

**Page types** (determined by slug prefix):

| Type | Prefix | What it stores |
|------|--------|----------------|
| Concept | `concept-` | A technical idea or theory — definition, how it works, edge cases |
| Strategy | `strategy-` | A trading strategy — setup, signals, risk rules, empirical notes |
| Source | `source-` | Summary of a book, paper, or article — key claims, quotes, context |
| Entity | `entity-` | A person, firm, or tool — background, notable work, opinions |
| Decision | `decision-` | Why you chose approach X over Y — alternatives considered, reversibility |
| Log | `log-` | Captured conversation insight or daily research note |
| Paper | `paper-` | Arxiv paper — abstract, methods, results, links to related concepts |

### Synonym-aware search

Pages have an `aliases` field listing alternate names for the same concept:

```yaml
aliases: ["mean reversion", "stat arb", "pairs trading"]
```

Searching for any of these terms finds the page — even if the query term never appears in the body text. This matters in quant where "momentum" = "trend following" = "time-series momentum" depending on the author.

### Inbox for quick capture

Don't want to think about where something belongs right now? Claude drops it in `vault/inbox/` with a timestamp. You can process it later, or ask Claude to sort through the inbox for you.

### Daily research log

Every session can anchor to today's date via `vault/wiki/log-YYYY-MM-DD.md`. Useful for tracking what you read, what questions came up, and what decisions were made on a given day.

### Arxiv integration

Claude can search Arxiv by topic and fetch full paper metadata in one step. Papers are saved to `vault/papers/` and automatically linked to related concept pages.

### Auto-timestamp hook

Every time a wiki page is edited, the `updated` field in frontmatter is updated automatically — no need to remember. Requires merging `hooks/hook-configs.json` into `~/.claude/settings.json`.

### Semantic search (optional)

For fuzzy conceptual search beyond keyword matching:

```bash
npm install -g @tobilu/qmd
qmd collection add ./vault --name llm-wiki
qmd context add llm-wiki "Quant trading research vault"
qmd embed
```

Once set up, the index rebuilds automatically after each Claude session.

### Vault health check

```bash
python hooks/validate-frontmatter.py vault/wiki
```

Checks all pages for missing required fields, invalid types, malformed slugs, and non-list aliases.

---

## Vault layout

```
vault/
├── inbox/     # Unprocessed quick-captures
├── raw/       # Original source text — never edited
├── wiki/      # All knowledge pages
├── papers/    # Arxiv papers
└── log.md     # Activity history
```

---

See [CLAUDE.md](CLAUDE.md) for full agent conventions and workflow details.
