import hashlib
import hmac
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from database import init_db
from config import GITHUB_WEBHOOK_SECRET
import agents


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("Issue Agent started. Listening for GitHub webhooks.")
    yield


app = FastAPI(title="Issue Agent", lifespan=lifespan)


def _verify_signature(payload: bytes, signature: str) -> bool:
    if not GITHUB_WEBHOOK_SECRET:
        return True
    expected = "sha256=" + hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    payload_bytes = await request.body()

    signature = request.headers.get("X-Hub-Signature-256", "")
    if not _verify_signature(payload_bytes, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    event = request.headers.get("X-GitHub-Event", "")
    data = json.loads(payload_bytes)
    repo = data.get("repository", {}).get("full_name", "")

    if event == "issues" and data.get("action") == "opened":
        issue = data["issue"]
        background_tasks.add_task(
            agents.handle_new_issue,
            repo,
            issue["number"],
            issue["title"],
            issue.get("body") or "(no description provided)",
        )

    elif event == "issue_comment" and data.get("action") == "created":
        sender = data.get("sender", {})
        if sender.get("type") == "Bot":
            return {"status": "ignored"}

        issue = data["issue"]
        comment = data["comment"]
        agent_signatures = ("**🐛", "**✨", "**💬", "**📚")
        if comment["body"].startswith(agent_signatures):
            return {"status": "ignored"}
        background_tasks.add_task(
            agents.handle_comment,
            repo,
            issue["number"],
            comment["body"],
        )

    return {"status": "ok"}


@app.get("/health")
def health():
    return {"status": "healthy"}
