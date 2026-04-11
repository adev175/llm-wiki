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

Each topic gets its own Markdown file with structured frontmatter. Pages are linked with `[[wikilinks]]` so nothing is an island. Claude never creates a page without first checking if one already exists.

Notes are automatically routed to a typed subfolder based on their `type` field:

| Type | Folder | Slug prefix | What it stores |
|------|--------|-------------|----------------|
| concept | `03-concepts/` | `concept-` | A technical idea or theory — definition, how it works, edge cases |
| strategy | `04-strategies/` | `strategy-` | A trading strategy — setup, signals, risk rules, empirical notes |
| source | `05-sources/` | `source-` | Summary of a book, paper, or article — key claims, quotes, context |
| entity | `06-entities/` | `entity-` | A person, firm, or tool — background, notable work, opinions |
| project | `02-projects/` | `project-` | Project plans, tracking, milestones |
| idea | `07-ideas/` | `idea-` | Brain dumps, explorations |
| decision | `08-decisions/` | `decision-` | Why you chose approach X over Y — alternatives considered, reversibility |
| log | `09-logs/` | `log-` | Captured conversation insight |
| daily | `01-daily/` | `log-YYYY-MM-DD` | Daily research anchor note |
| kaizen | `10-kaizen/` | `kaizen-` | System improvement notes |
| paper | `papers/` | `paper-` | Arxiv paper — abstract, methods, results, links to related concepts |

### Synonym-aware search

Pages have an `aliases` field listing alternate names for the same concept:

```yaml
aliases: ["mean reversion", "stat arb", "pairs trading"]
```

Searching for any of these terms finds the page — even if the query term never appears in the body text. This matters in quant where "momentum" = "trend following" = "time-series momentum" depending on the author.

### Inbox for quick capture

Don't want to think about where something belongs right now? Claude drops it in `vault/inbox/` with a timestamp. You can process it later, or ask Claude to sort through the inbox for you.

### Daily research log

Every session can anchor to today's date via `vault/01-daily/log-YYYY-MM-DD.md`. Useful for tracking what you read, what questions came up, and what decisions were made on a given day.

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
python hooks/validate-frontmatter.py vault/
```

Checks all pages across all typed folders for missing required fields, invalid types, malformed slugs, and non-list aliases.

---

## Vault layout

```
vault/
├── inbox/          # Unprocessed quick-captures
├── raw/            # Original source text — never edited
├── 01-daily/       # Daily research logs
├── 02-projects/    # Project tracking
├── 03-concepts/    # Technical concepts
├── 04-strategies/  # Trading strategies
├── 05-sources/     # Book / article / paper summaries
├── 06-entities/    # People, orgs, tools
├── 07-ideas/       # Brain dumps
├── 08-decisions/   # Decision records
├── 09-logs/        # Conversation captures
├── 10-kaizen/      # System improvement notes
├── papers/         # Arxiv papers
├── wiki/           # Legacy / unclassified fallback
├── _index.md       # Auto-generated catalog
└── log.md          # Activity history
```

> **Migration:** If upgrading from an older version with a flat `vault/wiki/`, run `wiki_migrate_folders()` once to move existing files into the correct typed subfolders.

---

See [CLAUDE.md](CLAUDE.md) for full agent conventions and workflow details.
