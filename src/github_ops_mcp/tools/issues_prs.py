from ..gh_wrapper import run_gh, run_gh_json
from ..validators import validate_owner_repo
from . import safe_call


@safe_call
def list_open_issues(owner_repo: str, label: str | None = None):
    """List open issues, optionally filtered by label."""
    validate_owner_repo(owner_repo)
    args = [
        "issue", "list", "--repo", owner_repo,
        "--state", "open",
        "--json", "number,title,labels,createdAt",
    ]
    if label:
        args += ["--label", label]

    data, err, code = run_gh_json(args)
    if code != 0 or data is None:
        raise RuntimeError(err or "gh issue list failed")

    return {
        "issues": [
            {
                "number": i.get("number"),
                "title": i.get("title"),
                "labels": [l.get("name") for l in (i.get("labels") or [])],
                "created_at": i.get("createdAt"),
            }
            for i in data
        ]
    }


@safe_call
def list_pull_requests(owner_repo: str):
    """List open PRs with CI check status."""
    validate_owner_repo(owner_repo)
    data, err, code = run_gh_json([
        "pr", "list", "--repo", owner_repo,
        "--json", "number,title,statusCheckRollup,author",
    ])
    if code != 0 or data is None:
        raise RuntimeError(err or "gh pr list failed")

    return {"prs": [_pr_row(p) for p in data]}


@safe_call
def get_pr_diff(owner_repo: str, pr_number: int):
    """Return the raw diff for a given PR."""
    validate_owner_repo(owner_repo)
    out, err, code = run_gh([
        "pr", "diff", str(pr_number), "--repo", owner_repo,
    ])
    if code != 0:
        raise RuntimeError(err or "gh pr diff failed")
    return {"diff_text": out}


def _pr_row(p: dict) -> dict:
    checks = p.get("statusCheckRollup") or []
    status = "none"
    if checks:
        states = {c.get("conclusion") or c.get("state") for c in checks}
        if "FAILURE" in states or "TIMED_OUT" in states:
            status = "failing"
        elif any(s in states for s in ("IN_PROGRESS", "PENDING", "QUEUED")):
            status = "pending"
        elif "SUCCESS" in states:
            status = "passing"
        else:
            status = "unknown"
    author = (p.get("author") or {}).get("login")
    return {
        "number": p.get("number"),
        "title": p.get("title"),
        "checks_status": status,
        "author": author,
    }
