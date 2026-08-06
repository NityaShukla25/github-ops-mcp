from ..config import README_TRUNCATE_CHARS
from ..gh_wrapper import run_gh, run_gh_json
from ..validators import validate_owner_repo
from . import safe_call


@safe_call
def search_repos(query: str, limit: int = 5):
    """Search GitHub for repositories matching a keyword."""
    data, err, code = run_gh_json([
        "search", "repos", query,
        "--limit", str(limit),
        "--json", "fullName,description,stargazersCount,url",
    ])
    if code != 0 or data is None:
        raise RuntimeError(err or "gh search failed")
    return [
        {
            "full_name": r.get("fullName"),
            "description": r.get("description"),
            "stars": r.get("stargazersCount", 0),
            "url": r.get("url"),
        }
        for r in data
    ]


@safe_call
def get_repo_info(owner_repo: str):
    """Fetch quick metadata for a repo."""
    validate_owner_repo(owner_repo)
    data, err, code = run_gh_json([
        "repo", "view", owner_repo,
        "--json", "description,stargazerCount,defaultBranchRef,issues,pullRequests,licenseInfo",
    ])
    if code != 0 or data is None:
        raise RuntimeError(err or "gh repo view failed")

    default_branch = (data.get("defaultBranchRef") or {}).get("name")
    license_info = data.get("licenseInfo") or {}
    return {
        "description": data.get("description"),
        "stars": data.get("stargazerCount", 0),
        "default_branch": default_branch,
        "open_issues": _count(data.get("issues")),
        "open_prs": _count(data.get("pullRequests")),
        "license": license_info.get("name") if license_info else None,
    }


@safe_call
def summarize_readme(owner_repo: str):
    """Return the README text (truncated) so the caller can summarize it."""
    validate_owner_repo(owner_repo)
    out, err, code = run_gh([
        "api", f"repos/{owner_repo}/readme",
        "-H", "Accept: application/vnd.github.raw",
    ])
    if code != 0:
        raise RuntimeError(err or "no README found")
    truncated = len(out) > README_TRUNCATE_CHARS
    return {
        "readme_text": out[:README_TRUNCATE_CHARS],
        "truncated": truncated,
    }


def _count(value):
    if isinstance(value, dict):
        return value.get("totalCount", 0)
    if isinstance(value, list):
        return len(value)
    if isinstance(value, int):
        return value
    return 0
