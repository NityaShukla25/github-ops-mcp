from ..gh_wrapper import run_gh_json
from ..validators import validate_owner_repo
from . import safe_call


@safe_call
def get_repo_stats(owner_repo: str):
    """Stars, forks, watchers, open issue/PR counts, size, timestamps."""
    validate_owner_repo(owner_repo)
    data, err, code = run_gh_json([
        "repo", "view", owner_repo,
        "--json", "stargazerCount,forkCount,watchers,issues,pullRequests,diskUsage,createdAt,updatedAt,pushedAt",
    ])
    if code != 0 or data is None:
        raise RuntimeError(err or "gh repo view failed")

    return {
        "stars": data.get("stargazerCount", 0),
        "forks": data.get("forkCount", 0),
        "watchers": _count(data.get("watchers")),
        "open_issues": _count(data.get("issues")),
        "open_prs": _count(data.get("pullRequests")),
        "size_kb": data.get("diskUsage", 0),
        "created_at": data.get("createdAt"),
        "updated_at": data.get("updatedAt"),
        "pushed_at": data.get("pushedAt"),
    }


@safe_call
def get_contributors(owner_repo: str, limit: int = 10):
    """Top contributors by commit count."""
    validate_owner_repo(owner_repo)
    data, err, code = run_gh_json([
        "api", f"repos/{owner_repo}/contributors?per_page={limit}",
    ])
    if code != 0 or data is None:
        raise RuntimeError(err or "gh api contributors failed")
    return {
        "contributors": [
            {"username": c.get("login"), "contributions": c.get("contributions", 0)}
            for c in data[:limit]
        ]
    }


@safe_call
def get_language_breakdown(owner_repo: str):
    """Language usage as percentages of bytes."""
    validate_owner_repo(owner_repo)
    data, err, code = run_gh_json(["api", f"repos/{owner_repo}/languages"])
    if code != 0 or data is None:
        raise RuntimeError(err or "gh api languages failed")

    total = sum(data.values()) or 1
    return {
        "languages": {lang: round(bytes_ * 100 / total, 2) for lang, bytes_ in data.items()}
    }


@safe_call
def get_topics(owner_repo: str):
    """Repo topics/tags."""
    validate_owner_repo(owner_repo)
    data, err, code = run_gh_json([
        "repo", "view", owner_repo, "--json", "repositoryTopics",
    ])
    if code != 0 or data is None:
        raise RuntimeError(err or "gh repo view failed")
    topics = data.get("repositoryTopics") or []
    if topics and isinstance(topics[0], dict):
        topics = [t.get("name") for t in topics if t.get("name")]
    return {"topics": topics}


@safe_call
def get_license(owner_repo: str):
    """License name for the repo."""
    validate_owner_repo(owner_repo)
    data, err, code = run_gh_json([
        "repo", "view", owner_repo, "--json", "licenseInfo",
    ])
    if code != 0 or data is None:
        raise RuntimeError(err or "gh repo view failed")
    info = data.get("licenseInfo") or {}
    return {"license": info.get("name") if info else None}


@safe_call
def get_releases(owner_repo: str, limit: int = 5):
    """Latest release plus recent release/tag history."""
    validate_owner_repo(owner_repo)
    data, err, code = run_gh_json([
        "release", "list", "--repo", owner_repo,
        "--limit", str(limit),
        "--json", "tagName,name,publishedAt",
    ])
    if code != 0:
        # Empty list is not an error
        if not err or "no releases" in err.lower():
            return {"releases": []}
        raise RuntimeError(err)
    if data is None:
        return {"releases": []}
    return {
        "releases": [
            {"tag": r.get("tagName"), "name": r.get("name"), "published_at": r.get("publishedAt")}
            for r in data
        ]
    }


def _count(value):
    if isinstance(value, dict):
        return value.get("totalCount", 0)
    if isinstance(value, list):
        return len(value)
    if isinstance(value, int):
        return value
    return 0
