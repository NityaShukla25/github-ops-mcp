import time

from ..gh_wrapper import run_gh, run_gh_json
from ..validators import validate_owner_repo
from . import safe_call


@safe_call
def get_default_branch_protection(owner_repo: str):
    """Branch protection status on the default branch. Requires admin — falls back to 'unknown'."""
    validate_owner_repo(owner_repo)
    info, err, code = run_gh_json([
        "repo", "view", owner_repo, "--json", "defaultBranchRef",
    ])
    if code != 0 or info is None:
        raise RuntimeError(err or "gh repo view failed")
    branch = (info.get("defaultBranchRef") or {}).get("name")
    if not branch:
        return {"protected": "unknown", "details": None}

    data, err, code = run_gh_json([
        "api", f"repos/{owner_repo}/branches/{branch}/protection",
    ])
    if code != 0:
        # 403/404 means we don't have visibility
        return {"protected": "unknown", "details": None}
    return {"protected": True, "details": data}


@safe_call
def get_commit_activity(owner_repo: str):
    """Weekly commit counts over the last year."""
    validate_owner_repo(owner_repo)

    # GitHub computes stats asynchronously; a 202 means "try again in a bit".
    for attempt in range(2):
        out, err, code = run_gh(["api", f"repos/{owner_repo}/stats/commit_activity"])
        if code == 0 and out.strip():
            import json
            data = json.loads(out)
            weekly = [w.get("total", 0) for w in data]
            return {"weekly_commits": weekly, "total_last_year": sum(weekly)}
        if attempt == 0:
            time.sleep(2)

    return {"weekly_commits": [], "total_last_year": 0, "note": "stats not ready yet"}


@safe_call
def get_network_info(owner_repo: str, limit: int = 10):
    """List of forks with owner and star counts."""
    validate_owner_repo(owner_repo)
    data, err, code = run_gh_json([
        "api", f"repos/{owner_repo}/forks?per_page={limit}",
    ])
    if code != 0 or data is None:
        raise RuntimeError(err or "gh api forks failed")

    return {
        "forks": [
            {
                "owner": (f.get("owner") or {}).get("login"),
                "stars": f.get("stargazers_count", 0),
                "url": f.get("html_url"),
            }
            for f in data[:limit]
        ]
    }
