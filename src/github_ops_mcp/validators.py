import re

OWNER_REPO_PATTERN = re.compile(r"^[\w.-]+/[\w.-]+$")
BRANCH_PATTERN = re.compile(r"^[\w./-]+$")


def validate_owner_repo(owner_repo: str) -> str:
    if not isinstance(owner_repo, str) or not OWNER_REPO_PATTERN.match(owner_repo):
        raise ValueError("owner_repo must be in 'owner/repo' format")
    return owner_repo


def validate_branch(branch: str) -> str:
    if not isinstance(branch, str) or not BRANCH_PATTERN.match(branch):
        raise ValueError("branch name contains invalid characters")
    return branch
