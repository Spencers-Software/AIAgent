# Issue Agent — Project Vision & Status

## What This Is

A multi-agent AI system that automatically responds to GitHub issues. When someone opens an issue on a GitHub repository, a Manager Agent reads it, classifies it, and routes it to the correct Specialist Agent. That agent then posts a helpful comment directly back on the GitHub issue — all without any human involvement.

Each issue gets its own isolated conversation thread stored in a local SQLite database, so agents never mix up context between issues.

---

## Why We Built It

The goal was to demonstrate a practical multi-agent orchestration pattern where:
- A **manager** makes routing decisions
- **Specialists** handle domain-specific responses
- Each "case" (GitHub issue) maintains its own persistent conversation history
- The system can handle follow-up comments too, resuming the correct agent's thread

This is a foundation that can be expanded into a full customer support system, internal helpdesk, or open-source project triage tool.

---

## Architecture

```
GitHub Issue Opened
        │
        ▼
  GitHub Webhook
  (POST /webhook)
        │
        ▼
   main.py (FastAPI)
   - Verifies request
   - Spawns background task
        │
        ▼
   agents.py — Manager Agent
   - Calls Groq LLM (llama-3.3-70b-versatile)
   - Classifies issue type
   - Chooses specialist agent
   - Adds GitHub label
        │
        ▼
   agents.py — Specialist Agent
   - Loads conversation history from SQLite
   - Calls Groq LLM with specialist system prompt
   - Posts comment to GitHub issue
   - Saves reply to SQLite
        │
        ▼
   GitHub Issue gets a comment posted automatically
```

### Follow-up Comments
When a user replies to an issue, the same webhook fires. The system looks up which agent was originally assigned, loads the full conversation history, and the specialist responds in context — like a real ongoing conversation.

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.9 |
| Web server | FastAPI + Uvicorn |
| LLM provider | Groq API (llama-3.3-70b-versatile) — free tier |
| GitHub integration | PyGitHub + GitHub Webhooks |
| Database | SQLite (local file: issues.db) |
| Tunnel (local dev) | localtunnel (npx localtunnel) |

---

## File Structure

```
C:\Users\spenc\issue-agent\
│
├── main.py          — FastAPI app, webhook receiver, signature verification
├── agents.py        — Manager + Specialist agent logic, Groq API calls
├── database.py      — SQLite setup, issue/message CRUD
├── github_client.py — Post comments, add labels via PyGitHub
├── config.py        — Loads environment variables
├── .env             — API keys and config (never commit this)
├── requirements.txt — Python dependencies
├── issues.db        — SQLite database (auto-created on first run)
└── VISION.md        — This file
```

---

## Agent Types

| Agent | Trigger | Behavior |
|---|---|---|
| **BugAgent** | issue_type = `bug` | Acknowledges bug, asks for repro steps, suggests fixes |
| **FeatureAgent** | issue_type = `feature_request` | Evaluates idea, asks about use cases |
| **QuestionAgent** | issue_type = `question` | Answers directly, provides code examples |
| **DocsAgent** | issue_type = `documentation` | Acknowledges gap, suggests what to cover |

The Manager Agent also assigns a **priority** (high/medium/low) and adds a GitHub label matching the issue type.

---

## Environment Variables (.env)

```
GROQ_API_KEY=your_groq_key_here
GITHUB_TOKEN=your_github_pat_here
GITHUB_WEBHOOK_SECRET=         ← left blank (signature check disabled for now)
DATABASE_PATH=issues.db
```

### GitHub Token Requirements
The GitHub Personal Access Token needs these permissions:
- Issues → Read and write
- Webhooks → Read and write
- Contents → Read and write
- Metadata → Read

---

## How to Run

### 1. Install dependencies
```bash
cd C:\Users\spenc\issue-agent
python -m pip install -r requirements.txt
python -m pip install requests python-dotenv PyGithub fastapi uvicorn
```

### 2. Start the server (Terminal 1)
```bash
cd C:\Users\spenc\issue-agent
python -m uvicorn main:app --reload --port 8080
```

### 3. Start the tunnel (Terminal 2)
```bash
npx localtunnel --port 8080 --subdomain issue-agent-spenc
```
Public URL will be: `https://issue-agent-spenc.loca.lt`

### 4. Verify it's running
```bash
curl http://localhost:8080/health
# should return: {"status":"healthy"}
```

---

## GitHub Webhook

- **Repository:** `https://github.com/Spencers-Software/AIAgent`
- **Webhook ID:** `608445785`
- **Payload URL:** `https://issue-agent-spenc.loca.lt/webhook`
- **Events:** Issues + Issue Comments
- **Secret:** (blank)

To update the webhook URL (if the tunnel URL changes):
```bash
curl -X PATCH \
  -H "Authorization: token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"config": {"url": "NEW_URL/webhook", "content_type": "json", "secret": "", "insecure_ssl": "0"}}' \
  "https://api.github.com/repos/Spencers-Software/AIAgent/hooks/608445785"
```

---

## What's Working

- [x] FastAPI webhook server receives GitHub events
- [x] HMAC signature verification (currently disabled, easy to re-enable)
- [x] Manager Agent classifies issues via LLM
- [x] Specialist agents respond with domain-appropriate comments
- [x] GitHub labels auto-created and applied
- [x] Per-issue conversation history stored in SQLite
- [x] Follow-up comment handling (same agent resumes thread)
- [x] Bot comment loop prevention (ignores Bot sender type)
- [x] localtunnel for local development
- [x] Groq API integration (free, fast, generous limits)

---

## Known Issues / Limitations

- The tunnel URL changes if you restart localtunnel without the `--subdomain` flag — always use `--subdomain issue-agent-spenc`
- If the tunnel goes down, GitHub webhooks will fail silently — check Recent Deliveries at `https://github.com/Spencers-Software/AIAgent/settings/hooks/608445785`
- Currently runs only while your computer is on — for 24/7 operation, deploy to a server (Railway, Render, DigitalOcean, etc.)
- Webhook secret verification is disabled — fine for development, should be re-enabled before any production use

---

## Next Steps (Future Work)

- [ ] Deploy to a cloud server so it runs 24/7 (Railway.app is easiest — free tier available)
- [ ] Re-enable webhook signature verification for security
- [ ] Add a web dashboard to view all issues and agent responses
- [ ] Support multiple repositories
- [ ] Add email notifications for high-priority issues
- [ ] Swap Groq for Claude (Anthropic) for higher quality responses when budget allows
- [ ] Add agent memory across issues (e.g. recognize repeat reporters)
- [ ] Slack/Discord notifications when new issues come in

---

## Groq API Notes

- Free tier is very generous (~14,400 requests/day, 30 req/min)
- Model used: `llama-3.3-70b-versatile` — fast and capable
- If rate limited, the system will raise an HTTP error (no retry logic currently for Groq, unlike the old Gemini setup)
- Groq dashboard: `https://console.groq.com`

---

*Last updated: 2026-04-21*
