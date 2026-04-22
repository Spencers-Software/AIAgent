from github import Github, GithubException
from config import GITHUB_TOKEN

_gh = Github(GITHUB_TOKEN)

SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".woff2",
    ".ttf", ".eot", ".pdf", ".zip", ".tar", ".gz", ".mp4", ".mp3",
    ".pyc", ".pyo", ".db", ".sqlite", ".lock",
}
SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build"}


def post_comment(repo_name: str, issue_number: int, body: str):
    repo = _gh.get_repo(repo_name)
    issue = repo.get_issue(issue_number)
    issue.create_comment(body)


def add_label(repo_name: str, issue_number: int, label: str):
    repo = _gh.get_repo(repo_name)
    issue = repo.get_issue(issue_number)
    try:
        repo.get_label(label)
    except Exception:
        colors = {
            "bug": "d73a4a",
            "feature_request": "a2eeef",
            "question": "d876e3",
            "documentation": "0075ca",
        }
        repo.create_label(label, colors.get(label, "ededed"))
    issue.add_to_labels(label)


def get_repo_tree(repo_name: str) -> list:
    """Returns filtered list of source file paths in the repo."""
    repo = _gh.get_repo(repo_name)
    tree = repo.get_git_tree(repo.default_branch, recursive=True)
    paths = []
    for item in tree.tree:
        if item.type != "blob":
            continue
        parts = item.path.split("/")
        if any(p in SKIP_DIRS for p in parts):
            continue
        ext = "." + item.path.rsplit(".", 1)[-1] if "." in item.path else ""
        if ext in SKIP_EXTENSIONS:
            continue
        paths.append(item.path)
    return paths[:300]


def get_file_contents(repo_name: str, path: str) -> tuple:
    """Returns (decoded_content, sha) for a file."""
    repo = _gh.get_repo(repo_name)
    file_obj = repo.get_contents(path)
    return file_obj.decoded_content.decode("utf-8", errors="replace"), file_obj.sha


def push_code_fix(
    repo_name: str,
    issue_number: int,
    file_path: str,
    new_content: str,
    commit_message: str,
    pr_title: str,
    pr_body: str,
) -> str:
    """Creates a branch, commits the fixed file, opens a PR. Returns the PR URL."""
    repo = _gh.get_repo(repo_name)
    default_branch = repo.default_branch
    base_sha = repo.get_branch(default_branch).commit.sha
    branch_name = f"fix/issue-{issue_number}"

    # Create branch (skip if it already exists)
    try:
        repo.create_git_ref(f"refs/heads/{branch_name}", base_sha)
    except GithubException as e:
        if e.status != 422:
            raise

    _, file_sha = get_file_contents(repo_name, file_path)
    repo.update_file(file_path, commit_message, new_content, file_sha, branch=branch_name)

    pr = repo.create_pull(
        title=pr_title,
        body=pr_body,
        head=branch_name,
        base=default_branch,
    )
    return pr.html_url
