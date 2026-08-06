from ..git_wrapper import run_git
from ..sandbox import resolve_repo_path
from ..validators import validate_branch
from . import safe_call


@safe_call
def get_status(repo_path: str):
    """Working-tree status split into staged / unstaged / untracked."""
    repo = resolve_repo_path(repo_path)
    out, err, code = run_git(["status", "--short"], cwd=repo)
    if code != 0:
        raise RuntimeError(err or "git status failed")

    staged, unstaged, untracked = [], [], []
    for line in out.splitlines():
        if not line:
            continue
        xy = line[:2]
        path = line[3:]
        if xy == "??":
            untracked.append(path)
            continue
        # X = staged, Y = unstaged
        if xy[0].strip():
            staged.append(path)
        if xy[1].strip():
            unstaged.append(path)
    return {"staged": staged, "unstaged": unstaged, "untracked": untracked}


@safe_call
def get_diff(repo_path: str, base: str, head: str):
    """Diff between two branches or commits."""
    repo = resolve_repo_path(repo_path)
    validate_branch(base)
    validate_branch(head)
    out, err, code = run_git(["diff", f"{base}..{head}"], cwd=repo)
    if code != 0:
        raise RuntimeError(err or "git diff failed")

    files_changed = sum(1 for l in out.splitlines() if l.startswith("diff --git "))
    return {"diff_text": out, "files_changed": files_changed}


@safe_call
def compare_branches(repo_path: str, branch_a: str, branch_b: str):
    """Ahead / behind counts between two branches."""
    repo = resolve_repo_path(repo_path)
    validate_branch(branch_a)
    validate_branch(branch_b)
    out, err, code = run_git(
        ["rev-list", "--left-right", "--count", f"{branch_a}...{branch_b}"],
        cwd=repo,
    )
    if code != 0:
        raise RuntimeError(err or "git rev-list failed")
    parts = out.strip().split()
    if len(parts) != 2:
        raise RuntimeError(f"unexpected rev-list output: {out!r}")
    ahead, behind = int(parts[0]), int(parts[1])
    return {"ahead": ahead, "behind": behind}
