# CLAUDE.md — unbiased

## What is this project?

**unbiased** is a developer context layer — a tool that extracts who you are
as a developer from your existing artifacts (GitHub, resume, manual input) and
makes that context available to every AI tool you use via an MCP server.

Core promise: *"Your AI tools already know your stack, your projects, and your
preferences. Zero re-explaining."*

---

## Critical rules — read before doing anything

1. **Do not move to the next phase until explicitly told to.**
   Complete the current phase fully. When done, stop and wait for clearance
   before touching anything in the next phase. Say clearly:
   > "Phase X is complete. Please review and confirm before I proceed to Phase X+1."

2. **Always update `requirements.txt` when adding or removing any library.**
   No exceptions. If you install something, it goes in `requirements.txt`
   immediately. If you remove something, remove it from `requirements.txt` too.

3. **Never assume a phase is done because the code compiles.**
   A phase is done only when its "Done when" condition is met and confirmed
   by the user.

---

## Tech stack

- **Backend:** FastAPI
- **Templates:** Jinja2
- **HTTP client:** httpx (async)
- **MCP server:** FastMCP (mounted into FastAPI)
- **Database:** PostgreSQL (via asyncpg or SQLAlchemy async)
- **LLM:** Gemini 2.5 Flash (via google-generativeai)
- **PDF parsing:** PyMuPDF (fitz)
- **Config:** python-dotenv
- **Deployment:** Render

---

## Environment variables

These live in `.env` locally and in Render's dashboard in production.
Never hardcode any of these.

```
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_REDIRECT_URI=http://localhost:8000/auth/callback
SECRET_KEY=
DATABASE_URL=
GEMINI_API_KEY=
```

---

## Project structure (target — build incrementally across phases)

```
unbiased/
├── main.py                  ← FastAPI app entry point
├── requirements.txt         ← always kept up to date
├── .env                     ← local env vars (never commit)
├── .env.example             ← committed, empty values
├── Procfile                 ← for Render: web: uvicorn main:app ...
├── routers/
│   ├── auth.py              ← GitHub OAuth routes
│   ├── dashboard.py         ← dashboard routes
│   └── mcp.py               ← MCP server mount
├── services/
│   ├── github.py            ← GitHub API extraction logic
│   ├── generator.py         ← LLM context generation (Gemini)
│   └── database.py          ← DB connection + queries
├── templates/
│   ├── index.html           ← landing page
│   ├── dashboard.html       ← post-login dashboard
│   └── setup.html           ← MCP setup instructions
└── mcp_tools/
    └── tools.py             ← FastMCP tool definitions
```

---

## Phases

---

### Phase 1 — GitHub OAuth
**Goal:** A real user can visit the deployed URL, log in with their GitHub
account, and land on a dashboard showing their GitHub username and avatar.

**What to build:**
- FastAPI app with SessionMiddleware
- `GET /` — landing page with "Connect GitHub" button
- `GET /login` — redirects to GitHub OAuth URL with correct scopes
- `GET /auth/callback` — exchanges code for access token, fetches `/user`
  from GitHub API, stores token in session, redirects to `/dashboard`
- `GET /dashboard` — shows username, avatar, placeholder "Extraction coming soon"
- GitHub OAuth scopes: `read:user repo`
- Render-ready: reads `PORT` from env, `0.0.0.0` host binding
- `Procfile` with: `web: uvicorn main:app --host 0.0.0.0 --port $PORT`

**Libraries needed (add all to requirements.txt):**
```
fastapi
uvicorn
httpx
jinja2
python-dotenv
itsdangerous
starlette
```

**Done when:** A real user visits the Render URL, clicks "Connect GitHub",
completes GitHub OAuth, and sees their GitHub username and avatar on the
dashboard. No errors. Works end to end.

---

### Phase 2 — GitHub Extraction
**Goal:** After login, the user's GitHub data is read via API and stored
in the database.

**What to build:**
- PostgreSQL connection (add asyncpg + SQLAlchemy async or just asyncpg)
- `users` table: `id`, `github_username`, `github_token`, `created_at`
- `raw_github_data` table: `user_id`, `repos_json`, `languages_json`,
  `readmes_json`, `extracted_at`
- GitHub extraction service:
  - Fetch up to 50 most recently updated repos (exclude forks)
  - For each repo: fetch languages, README content (base64 decode),
    topics, and contents of `requirements.txt` / `package.json` /
    `pom.xml` / `go.mod` if they exist
  - Filter: skip repos with zero commits in last 2 years
- Trigger extraction automatically after OAuth callback completes
- Show extraction status on dashboard

**Libraries needed (add all to requirements.txt):**
```
asyncpg
sqlalchemy[asyncio]
```

**Done when:** After login, the database has a populated row for the user
with their raw GitHub repo data. Dashboard shows "X repos scanned."

---

### Phase 3 — Context Generation
**Goal:** Raw GitHub data is turned into structured markdown files using
Gemini. User can also provide manual input for things GitHub can't infer.

**What to build:**
- `context_files` table: `user_id`, `filename`, `content`, `generated_at`
- Gemini 2.5 Flash prompts to generate:
  - `stack.md` — languages, frameworks, tools inferred from repos
  - `projects.md` — project summaries from repo names + READMEs
  - `experience.md` — inferred from repo history and descriptions
- Manual input form on dashboard for:
  - `goals.md` — "What are you currently working toward?"
  - `learning.md` — "What are you currently learning?"
- Store all generated files in `context_files` table
- Display all files on dashboard (read-only for now)

**Libraries needed (add all to requirements.txt):**
```
google-generativeai
```

**Done when:** After login and extraction, the dashboard shows auto-generated
`stack.md` and `projects.md`. User can fill in goals and learning manually.
All files stored in DB.

---

### Phase 4 — MCP Server
**Goal:** Claude Desktop and Cursor can connect to unbiased and access the
user's context via MCP tools.

**What to build:**
- `user_tokens` table: `user_id`, `mcp_token` (UUID, generated post-OAuth)
- FastMCP server mounted at `/mcp` inside the FastAPI app
- MCP tools:
  - `get_stack()` → returns `stack.md` for the authenticated user
  - `get_projects()` → returns `projects.md`
  - `get_full_context()` → returns all markdown files merged
  - `get_context_for(task: str)` → LLM picks which files are relevant
- Per-user auth: bearer token in Authorization header
- Dashboard shows:
  - User's unique MCP token (copy button)
  - Copy-paste MCP config JSON for Claude Desktop
  - Copy-paste config for Cursor

**Libraries needed (add all to requirements.txt):**
```
fastmcp
```

**Done when:** User copies MCP config into Claude Desktop config file,
restarts Claude, asks "what's my tech stack?" and Claude correctly returns
their `stack.md` content.

---

### Phase 5 — Auto Refresh + Editing
**Goal:** Context stays accurate over time. User can correct what the LLM
got wrong.

**What to build:**
- Daily background job to re-scan GitHub for each user (APScheduler or
  Render cron job)
- "Refresh now" button on dashboard (POST `/refresh`)
- Inline editing of each markdown file on dashboard
- Save edits back to `context_files` table
- Show `last_updated` timestamp per file

**Libraries needed (add all to requirements.txt):**
```
apscheduler
```

**Done when:** User's `stack.md` updates when they push a new project.
User can edit any file and changes persist.

---

### Phase 6 — Polish + Launch
**Goal:** Product is ready to share publicly and list on Product Hunt.

**What to build:**
- Proper landing page with value proposition and screenshots
- Onboarding flow / setup guide page (`/setup`)
- Error handling for all failure cases (GitHub API down, Gemini error, etc.)
- Empty states for new users with no repos
- Basic logging
- Product Hunt listing under: **LLM Memory** + **AI Coding Agents**

**Done when:** You would feel comfortable sharing the link with strangers.

---

## Render deployment notes

- Set all env vars in Render dashboard (not in code)
- `GITHUB_REDIRECT_URI` must be updated to the Render public URL:
  `https://unbiased.onrender.com/auth/callback`
- Update the callback URL in GitHub OAuth app settings to match
- GitHub OAuth app settings allow multiple callback URLs —
  keep localhost and Render URL both registered during development
- Free tier spins down after inactivity — acceptable for v1

---

## What unbiased is NOT

- Not a general assistant (no chat interface)
- Not a team tool (individual dev context only for v1)
- Not storing code — only metadata, language stats, README text, markdown files
- Not writing to GitHub — read-only access only