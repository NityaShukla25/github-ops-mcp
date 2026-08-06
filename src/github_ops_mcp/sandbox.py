from pathlib import Path

from .config import WORKSPACE_ROOT
from .validators import validate_owner_repo


def repo_dir_name(owner_repo: str) -> str:
    validate_owner_repo(owner_repo)
    owner, repo = owner_repo.split("/", 1)
    return f"{owner}__{repo}"


def resolve_repo_path(repo_path: str) -> Path:
    p = (WORKSPACE_ROOT / repo_path).resolve() if not Path(repo_path).is_absolute() else Path(repo_path).resolve()
    try:
        p.relative_to(WORKSPACE_ROOT)
    except ValueError:
        raise ValueError(f"repo_path must be inside workspace ({WORKSPACE_ROOT})")
    return p


def resolve_file_in_repo(repo_path: str, filepath: str) -> Path:
    repo = resolve_repo_path(repo_path)
    target = (repo / filepath).resolve()
    try:
        target.relative_to(repo)
    except ValueError:
        raise ValueError("filepath escapes the repo directory")
    return target
