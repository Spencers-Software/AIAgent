import json
import requests
from config import GROQ_API_KEY
from database import create_issue, get_issue, update_issue, add_message, get_messages
import github_client

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

MANAGER_SYSTEM = """You are the manager agent for a GitHub issue tracker. Your job is to:
1. Read the incoming GitHub issue
2. Classify it into exactly one type
3. Route it to the correct specialist agent

Respond with JSON only — no other text.

Issue types and their specialist agents:
- bug → BugAgent (crashes, errors, unexpected behavior)
- feature_request → FeatureAgent (new functionality requests, enhancements)
- question → QuestionAgent (how-to questions, usage help)
- documentation → DocsAgent (missing docs, unclear docs, doc improvements)

JSON schema:
{
  "issue_type": "bug | feature_request | question | documentation",
  "assigned_agent": "BugAgent | FeatureAgent | QuestionAgent | DocsAgent",
  "priority": "high | medium | low",
  "reasoning": "one sentence explanation"
}"""

SPECIALIST_SYSTEMS = {
    "BugAgent": """You are a senior software engineer specializing in bug triage. You respond to GitHub issues.

When analyzing bug reports:
- Acknowledge the issue clearly and empathetically
- If enough info: suggest likely causes and potential fixes
- If missing info: ask targeted clarifying questions (steps to reproduce, OS/version, error messages, expected vs actual behavior)
- Keep responses technical but accessible
- Be concise — no fluff

Start your comment with: **🐛 Bug Report Received**""",

    "FeatureAgent": """You are a product engineer who evaluates feature requests. You respond to GitHub issues.

When analyzing feature requests:
- Acknowledge the idea and show genuine interest
- Evaluate whether it fits the project scope
- Ask clarifying questions about use cases and expected behavior if needed
- Note any similar existing functionality
- Be constructive and encouraging

Start your comment with: **✨ Feature Request Received**""",

    "QuestionAgent": """You are a helpful support engineer. You respond to GitHub issues.

When answering questions:
- Answer directly and clearly
- Include code examples where relevant
- If the question is ambiguous, ask one focused clarifying question
- Keep it friendly and approachable

Start your comment with: **💬 Question Received**""",

    "DocsAgent": """You are a technical writer. You respond to GitHub issues about documentation.

When handling documentation requests:
- Acknowledge what documentation is missing or unclear
- Ask clarifying questions about scope, audience, and format if needed
- Suggest what the documentation should cover

Start your comment with: **📚 Documentation Request Received**""",
}

FILE_SELECTOR_SYSTEM = """You are a senior software engineer. Given a GitHub issue and a list of files in the repository, identify which single file is most likely the one that needs to be changed to resolve the issue.

Respond with JSON only — no other text.

JSON schema:
{
  "file_path": "path/to/file.py or null if cannot determine",
  "confidence": "high | medium | low",
  "reasoning": "one sentence explanation"
}

Return file_path as null if:
- The issue is a question or documentation request (no code change needed)
- You cannot confidently identify a single file to change
- The fix would require changes across many files"""

CODE_FIX_SYSTEM = """You are a senior software engineer writing a code fix for a GitHub issue.

You will be given:
1. The GitHub issue (title + description)
2. The full content of a source file

Your job: produce the complete fixed version of that file with the bug fixed or feature added.

Rules:
- Return the ENTIRE file content, not just the changed lines
- Make the minimal change needed to fix the issue
- Do not add unrelated refactors or style changes
- If the fix is genuinely unclear or risky, set "can_fix" to false

Respond with JSON only — no other text.

JSON schema:
{
  "can_fix": true,
  "fixed_content": "...complete file content...",
  "commit_message": "fix: one line description of what was changed",
  "pr_title": "Fix: short description (closes #<issue_number>)",
  "change_summary": "2-3 sentences describing exactly what was changed and why"
}

If you cannot fix it:
{
  "can_fix": false,
  "reason": "explanation of why a fix cannot be generated"
}"""


def _groq_chat(system_prompt: str, history: list, last_message: str) -> str:
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": last_message})

    resp = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={"model": GROQ_MODEL, "messages": messages, "temperature": 0.3},
        timeout=60,
    )
    if not resp.ok:
        print(f"[Groq Error] {resp.status_code}: {resp.text}")
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _parse_json(text: str) -> dict:
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


def _run_manager(title: str, body: str) -> dict:
    text = _groq_chat(MANAGER_SYSTEM, [], f"Title: {title}\n\n{body}")
    return _parse_json(text)


def _run_specialist(issue_id: int, agent_name: str, repo: str, issue_number: int):
    messages = get_messages(issue_id)

    clean = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "assistant"
        if clean and clean[-1]["role"] == role:
            clean[-1] = {"role": role, "content": msg["content"]}
        else:
            clean.append({"role": role, "content": msg["content"]})

    if not clean:
        return

    last_message = clean[-1]["content"]
    history = clean[:-1]

    reply = _groq_chat(SPECIALIST_SYSTEMS[agent_name], history, last_message)

    add_message(issue_id, "assistant", reply)
    github_client.post_comment(repo, issue_number, reply)


def _attempt_code_fix(repo: str, issue_number: int, title: str, body: str):
    """Tries to generate and push a code fix PR. Silently skips if it can't."""
    print(f"[CodeFix] Analyzing repo '{repo}' for a fix to issue #{issue_number}...")

    try:
        file_list = github_client.get_repo_tree(repo)
    except Exception as e:
        print(f"[CodeFix] Could not fetch repo tree: {e}")
        return

    if not file_list:
        print("[CodeFix] Repo tree is empty, skipping.")
        return

    file_list_str = "\n".join(file_list)
    selector_prompt = (
        f"Issue Title: {title}\n\nIssue Body:\n{body}\n\nRepository files:\n{file_list_str}"
    )

    try:
        selector_raw = _groq_chat(FILE_SELECTOR_SYSTEM, [], selector_prompt)
        selection = _parse_json(selector_raw)
    except Exception as e:
        print(f"[CodeFix] File selector failed: {e}")
        return

    if not selection.get("file_path"):
        print(f"[CodeFix] No file identified ({selection.get('reasoning', '')}), skipping.")
        return

    if selection.get("confidence") == "low":
        print(f"[CodeFix] Low confidence on file selection, skipping.")
        return

    file_path = selection["file_path"]
    print(f"[CodeFix] Selected file: {file_path} ({selection.get('confidence')} confidence)")

    try:
        file_content, _ = github_client.get_file_contents(repo, file_path)
    except Exception as e:
        print(f"[CodeFix] Could not fetch {file_path}: {e}")
        return

    fix_prompt = (
        f"Issue #{issue_number} — {title}\n\nIssue description:\n{body}\n\n"
        f"File to fix: {file_path}\n\nCurrent file content:\n```\n{file_content}\n```"
    )

    try:
        fix_raw = _groq_chat(CODE_FIX_SYSTEM, [], fix_prompt)
        fix = _parse_json(fix_raw)
    except Exception as e:
        print(f"[CodeFix] Code fix generation failed: {e}")
        return

    if not fix.get("can_fix"):
        print(f"[CodeFix] Agent declined to fix: {fix.get('reason', '')}")
        return

    pr_body = (
        f"## AI-Generated Fix\n\n"
        f"This PR was automatically generated in response to issue #{issue_number}.\n\n"
        f"**What changed:** {fix['change_summary']}\n\n"
        f"**File modified:** `{file_path}`\n\n"
        f"> ⚠️ This is an AI-generated fix. Please review carefully before merging.\n\n"
        f"Closes #{issue_number}"
    )

    try:
        pr_url = github_client.push_code_fix(
            repo_name=repo,
            issue_number=issue_number,
            file_path=file_path,
            new_content=fix["fixed_content"],
            commit_message=fix["commit_message"],
            pr_title=fix["pr_title"],
            pr_body=pr_body,
        )
        print(f"[CodeFix] PR opened: {pr_url}")

        github_client.post_comment(
            repo,
            issue_number,
            f"🔧 **Automated Fix Available**\n\nI've opened a pull request with a proposed fix: {pr_url}\n\n"
            f"**Summary of changes:** {fix['change_summary']}\n\n"
            f"> This is an AI-generated fix — please review it before merging.",
        )
    except Exception as e:
        print(f"[CodeFix] Failed to push PR: {e}")


def handle_new_issue(repo: str, issue_number: int, title: str, body: str):
    print(f"[Manager] New issue #{issue_number} in {repo}: {title}")

    issue_id = create_issue(repo, issue_number)
    add_message(issue_id, "user", f"**{title}**\n\n{body}")

    routing = _run_manager(title, body)
    print(f"[Manager] Routed to {routing['assigned_agent']} ({routing['issue_type']}, {routing['priority']} priority)")

    update_issue(issue_id, routing["issue_type"], routing["assigned_agent"])
    github_client.add_label(repo, issue_number, routing["issue_type"])

    _run_specialist(issue_id, routing["assigned_agent"], repo, issue_number)
    print(f"[{routing['assigned_agent']}] Responded to #{issue_number}")

    _attempt_code_fix(repo, issue_number, title, body)


def handle_comment(repo: str, issue_number: int, comment_body: str):
    issue = get_issue(repo, issue_number)
    if not issue or not issue["assigned_agent"]:
        print(f"[Warning] Comment on unknown issue #{issue_number} in {repo}, skipping")
        return

    print(f"[{issue['assigned_agent']}] Follow-up on #{issue_number} in {repo}")
    add_message(issue["id"], "user", comment_body)
    _run_specialist(issue["id"], issue["assigned_agent"], repo, issue_number)
