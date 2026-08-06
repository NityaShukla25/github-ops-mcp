from . import safe_call
from .discovery import summarize_readme
from .repo_stats import (
    get_contributors,
    get_language_breakdown,
    get_license,
    get_releases,
    get_repo_stats,
    get_topics,
)


@safe_call
def generate_repo_summary(owner_repo: str):
    """Aggregate stats + contributors + languages + topics + license + latest release + README."""
    warnings: list[str] = []

    def _grab(fn, *args, **kwargs):
        result = fn(*args, **kwargs)
        if result.get("ok"):
            return result["data"]
        warnings.append(f"{fn.__name__}: {result.get('error')}")
        return None

    stats = _grab(get_repo_stats, owner_repo)
    contributors = _grab(get_contributors, owner_repo)
    languages = _grab(get_language_breakdown, owner_repo)
    topics = _grab(get_topics, owner_repo)
    license_info = _grab(get_license, owner_repo)
    releases = _grab(get_releases, owner_repo, 1)
    readme = _grab(summarize_readme, owner_repo)

    latest_release = None
    if releases and releases.get("releases"):
        latest_release = releases["releases"][0]

    return {
        "stats": stats,
        "contributors": (contributors or {}).get("contributors", []),
        "languages": (languages or {}).get("languages", {}),
        "topics": (topics or {}).get("topics", []),
        "license": (license_info or {}).get("license"),
        "latest_release": latest_release,
        "readme_summary_text": (readme or {}).get("readme_text", ""),
        "warnings": warnings,
    }
