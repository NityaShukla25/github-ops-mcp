from ..config import WORKSPACE_ROOT
from ..git_wrapper import run_git
from ..sandbox import repo_dir_name, resolve_repo_path
from ..validators import validate_owner_repo
from . import safe_call


@safe_call
def clone_repo(owner_repo: str):
    """Clone a repo into the sandboxed workspace (no-op if already cloned)."""
    validate_owner_repo(owner_repo)
    dest = WORKSPACE_ROOT / repo_dir_name(owner_repo)

    if dest.exists() and (dest / ".git").exists():
        return {"repo_path": str(dest), "already_existed": True}

    url = f"https://github.com/{owner_repo}.git"
    out, err, code = run_git(["clone", url, str(dest)])
    if code != 0:
        raise RuntimeError(err.strip() or "git clone failed")

    return {"repo_path": str(dest), "already_existed": False}


@safe_call
def pull_latest(repo_path: str):
    """Run `git pull` in an already-cloned repo."""
    repo = resolve_repo_path(repo_path)
    out, err, code = run_git(["pull"], cwd=repo)
    return {
        "output": (out + err).strip(),
        "success": code == 0,
    }
