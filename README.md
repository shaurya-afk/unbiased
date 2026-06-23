# unbiased

Reads your GitHub once and serves your developer identity — stack, 
projects, languages, and contribution patterns — to Claude, Cursor, 
and any MCP client over a single remote URL.

Built for AI assistants that need real developer context, not 
self-reported profiles.

---

## What it does

Connect unbiased to your MCP client and it exposes tools that pull 
live context from your GitHub:

| Tool | Description |
|---|---|
| `get_stack` | Returns the developer's tech stack — languages, frameworks, and tools |
| `get_projects` | Returns summaries of notable GitHub projects |
| `get_full_context` | Returns all developer context files merged into a single document |
| `get_context_for` | Given a task description, returns only the context most relevant to it |

> `get_context_for` is task-aware — describe what you're building and it 
> filters your context down to only what's relevant, using an LLM to rank 
> and trim before returning.

Claude or Cursor can then use this context automatically — no 
copy-pasting your resume into every conversation.

**Example:** Ask Claude *"review my architecture given my background"* 
and it pulls your actual stack before responding.

---

## Connect (Remote — no setup needed)

1. Visit [unbiased-ax79.onrender.com](https://unbiased-ax79.onrender.com) 
   and connect your GitHub via OAuth
2. Copy your personal MCP URL from the dashboard
3. Add it to your MCP client config:

**Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "unbiased": {
      "command": "npx",
      "args": ["mcp-remote", "https://unbiased-ax79.onrender.com/mcp/YOUR_TOKEN"]
    }
  }
}
```

**Cursor** (Settings → MCP → Add Server):
https://unbiased-ax79.onrender.com/mcp/YOUR_TOKEN

---

## Sample output — `get_stack`

\```
## Languages
Python, Java, TypeScript

## Frameworks
FastAPI, Spring Boot, LangGraph, Next.js

## Databases
PostgreSQL, MongoDB, Redis, ChromaDB

## Cloud
AWS (ECS, S3), Render, Docker
\```

---

## Self-host

```bash
git clone https://github.com/shaurya-afk/unbiased
cd unbiased
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in values below
uvicorn main:app --reload
```

### Environment variables

| Variable | Description |
|---|---|
| `GITHUB_CLIENT_ID` | GitHub OAuth App client ID |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth App client secret |
| `GITHUB_REDIRECT_URI` | `http://localhost:8000/auth/callback` for local |
| `SECRET_KEY` | Random string, 32+ chars |
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host/db` |
| `GEMINI_API_KEY` | Google AI Studio API key |

---

## Tech

FastAPI · FastMCP · OAuth 2.1 · PostgreSQL · Render
