# GitHub Ops MCP Server — Project Plan

**Project name:** `github-ops-mcp`
**Type:** Self help 
**Language:** Python 3.11+
**SDK:** Official `mcp` Python SDK (FastMCP style)
**Underlying tools:** `git` CLI + `gh` (GitHub CLI) via `subprocess`
**Transports:** Both `stdio` (local, e.g. Claude Desktop) and `HTTP/SSE` (remote, accessible over network)

---

## 1. Goal

Build an MCP server that lets an LLM (Claude or any MCP client) search GitHub repositories, clone them locally, and perform common git/GitHub operations (branch management, diffs, issues, PRs, repo insights) — all through a clean, sandboxed, read-mostly tool interface. No custom auth handling — relies entirely on the user's already-configured `gh auth login` session and local git credentials.

**Tool count:** 25 total, split into two tiers:
- **MVP tier (20 tools)** — build and demo these first. This is the "done" definition for the project.
- **Stretch tier (5 tools)** — `get_default_branch_protection`, `get_commit_activity`, `get_network_info`, `get_file_history`, `compare_branches`. Clearly labeled extras to add only if time permits. Do not let these block the MVP demo or the viva.

---

## 2. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Simple, fast to build, great subprocess support |
| MCP SDK | `mcp` (official Python SDK), FastMCP decorators | Least boilerplate, official support |
| Git operations | `git` CLI via `subprocess` | No need to reimplement git internals |
| GitHub API operations | `gh` CLI via `subprocess` | Auth already handled by `gh auth login`; avoids token management |
| Transport (local) | `stdio` | Works directly with Claude Desktop / Claude Code |
| Transport (remote) | `HTTP` with SSE (`mcp.server.fastmcp` supports `streamable-http` / `sse`) | Lets it run as a hosted service, demoable via browser/Postman too |
| Config | `.env` + a `config.py` | Workspace path, allowed commands, host/port |
| Packaging | `pyproject.toml` + `uv` or `pip` | Standard modern Python packaging |

---

## 3. Folder Structure

```
github-ops-mcp/
├── pyproject.toml
├── README.md
├── plan.md                    # this file
├── .env.example
├── .gitignore
├── workspace/                 # sandboxed clone destination (gitignored)
├── src/
│   └── github_ops_mcp/
│       ├── __init__.py
│       ├── server.py           # FastMCP app, tool registrations, transport entrypoint
│       ├── config.py           # paths, guardrail whitelist, env loading
│       ├── git_wrapper.py       # subprocess wrapper for `git` commands
│       ├── gh_wrapper.py        # subprocess wrapper for `gh` commands
│       ├── sandbox.py           # path sanitization + workspace enforcement
│       ├── validators.py        # shared owner_repo format validation (used by every tool taking owner_repo)
│       └── tools/
│           ├── __init__.py
│           ├── discovery.py     # search_repos, get_repo_info, summarize_readme
│           ├── setup.py         # clone_repo, pull_latest
│           ├── branches.py      # list_branches, checkout_branch, list_commits, get_file_history
│           ├── comparison.py    # get_status, get_diff, compare_branches
│           ├── issues_prs.py    # list_open_issues, list_pull_requests, get_pr_diff
│           ├── repo_stats.py    # get_repo_stats, get_contributors, get_language_breakdown,
│           │                    # get_topics, get_license, get_releases (MVP)
│           ├── repo_stats_ext.py# get_default_branch_protection, get_commit_activity,
│           │                    # get_network_info (stretch)
│           └── repo_summary.py  # generate_repo_summary (composite, MVP)
└── tests/
    ├── test_git_wrapper.py
    ├── test_sandbox.py
    └── test_tools.py
```

---

## 4. Core Design Principles

1. **No custom auth.** Server assumes `gh auth login` and git SSH/HTTPS credentials are already set up on the host machine. The server code never touches tokens.
2. **Sandboxed workspace.** All clones live under `./workspace/<owner>__<repo>/`. No tool accepts an arbitrary filesystem path — only a `repo_path` that is validated to be inside `WORKSPACE_ROOT`.
3. **Command whitelist (guardrails).** Every subprocess call is built from a fixed, hardcoded list of allowed git/gh subcommands. User-supplied values (branch names, queries, filenames) are passed as **argument list items**, never interpolated into a shell string — this avoids shell injection entirely (`subprocess.run([...], shell=False)`).
4. **No destructive operations.** Explicitly excluded: `push`, `push --force`, `reset --hard`, `rebase`, `clean -fd`, `branch -D`, `gh repo delete`, `gh repo edit`. No write actions to GitHub itself exist in the final tool list — everything either reads from GitHub/git or writes only to the local sandboxed workspace.
5. **Read-mostly by default.** 23 of 25 tools are pure read operations. Only `checkout_branch(create_new=True)`, `clone_repo`, and `pull_latest` touch the local filesystem, and only inside the sandboxed workspace — never GitHub itself.
6. **Dual transport.** Same tool definitions, two entrypoints:
   - `python -m github_ops_mcp.server --stdio` → local, for Claude Desktop/Code
   - `python -m github_ops_mcp.server --http --port 8000` → remote, for hosted/demo use

---

## 5. Transport Modes

### 5.1 stdio (local)
Standard MCP transport over stdin/stdout. Used when the client (e.g. Claude Desktop) launches the server as a subprocess.

```json
{
  "mcpServers": {
    "github-ops": {
      "command": "python",
      "args": ["-m", "github_ops_mcp.server", "--stdio"]
    }
  }
}
```

### 5.2 HTTP / SSE (remote)
FastMCP supports `streamable-http` transport out of the box. This lets the server run as a standalone process reachable over the network — good for a demo where the interviewer can hit an endpoint directly, or where the server runs on a cloud VM and multiple clients connect.

```bash
python -m github_ops_mcp.server --http --host 0.0.0.0 --port 8000
```

Client config (remote):
```json
{
  "mcpServers": {
    "github-ops-remote": {
      "url": "http://<server-ip>:8000/mcp"
    }
  }
}
```

`server.py` should branch on a CLI flag:
```python
import argparse
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("github-ops-mcp")

# ... register all tools via @mcp.tool() ...

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stdio", action="store_true")
    parser.add_argument("--http", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.http:
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
```

---

## 6. Sandbox & Guardrails Module

**Parameter convention — `owner_repo` (applies to every tool that takes it):**
- Format is always a single string: `"owner/repo"` (e.g. `"facebook/react"`, `"torvalds/linux"`) — combining the GitHub username/organization and the repository name with a `/`. This is NOT just the repo name by itself, since repo names alone aren't unique on GitHub. It's also exactly the format the `gh` CLI itself expects (e.g. `gh repo view facebook/react`), so it can be passed straight through without reformatting.
- Every tool signature in §7 that lists `owner_repo: str` as an input uses this exact format. Do not split it into separate `owner: str, repo: str` parameters — keep it as one string to match `gh` CLI conventions and to keep tool signatures consistent across the whole server.
- **Validate before use, in every tool that accepts it** (not just the `gh api`-based ones): reject anything that doesn't match `^[\w.-]+/[\w.-]+$` — no missing slash, no extra slashes, no spaces, no leading/trailing slash. Return a clear `{"ok": False, "error": "owner_repo must be in 'owner/repo' format"}` rather than letting a malformed value reach a `gh`/`git` subprocess call.
- Put this validator in a shared `validators.py` (see structure below) and import it into every tool module that takes `owner_repo` — do not duplicate the regex per-file.

**`validators.py`** *(new shared module)*
- `OWNER_REPO_PATTERN = re.compile(r"^[\w.-]+/[\w.-]+$")`
- `validate_owner_repo(owner_repo: str) -> str`: raises `ValueError` if it doesn't match the pattern; otherwise returns the string unchanged (so it can be used as `owner_repo = validate_owner_repo(owner_repo)` at the top of every tool function).
- Called at the very first line of every tool in `discovery.py`, `repo_stats.py`, `repo_summary.py`, and `issues_prs.py` — i.e. every tool whose input table above lists `owner_repo: str`. Tools that take `repo_path: str` instead (setup/branches/comparison groups) use `resolve_repo_path` from `sandbox.py`, not this validator.

**`sandbox.py`**
- `WORKSPACE_ROOT = Path("./workspace").resolve()`
- `resolve_repo_path(repo_path: str) -> Path`: joins against `WORKSPACE_ROOT`, resolves `..` traversal, raises `ValueError` if the resolved path escapes the root.
- `repo_dir_name(owner_repo: str) -> str`: converts `"owner/repo"` → `"owner__repo"` (calls `validate_owner_repo` first).

**`git_wrapper.py`**
- `ALLOWED_GIT_SUBCOMMANDS = {"clone", "pull", "branch", "checkout", "status", "diff", "log", "rev-list", "shortlog"}`
- `run_git(args: list[str], cwd: Path) -> tuple[str, str, int]`: validates `args[0]` is in the whitelist before calling `subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=30, shell=False)`.

**`gh_wrapper.py`**
- `ALLOWED_GH_SUBCOMMANDS = {"search", "repo", "issue", "pr", "release", "api"}` (`"api"` added for the Repo Stats & Insights group — `get_contributors`, `get_language_breakdown`, `get_default_branch_protection`, `get_commit_activity`, `get_network_info` all call `gh api repos/...`)
- For `"api"` calls specifically, additionally whitelist the allowed endpoint path *prefixes* (`repos/{owner}/{repo}/contributors`, `.../languages`, `.../forks`, `.../stats/commit_activity`, `.../branches/{branch}/protection`) so an arbitrary API path can't be requested — validate `owner_repo` format (`^[\w.-]+/[\w.-]+$`) before building any endpoint string.
- `run_gh(args: list[str], cwd: Path | None = None) -> tuple[str, str, int]`: same validation pattern, calls `gh` CLI with `--json` flags wherever available for structured output.

**Explicitly blocked, enforced at the wrapper level (raise `PermissionError` if attempted):**
`push`, `push --force`, `reset --hard`, `rebase`, `clean`, `branch -D`/`branch -d` (delete), `gh repo delete`, `gh repo edit`.

---

## 7. Final Tool List (25 tools — 20 MVP + 5 stretch)

### 📊 Repo Stats & Insights *(new group)*

**1. `get_repo_stats`** — *MVP*
- Description: Stars, forks, watchers, open issues/PR counts, repo size, created/updated/pushed dates.
- Input: `owner_repo: str`
- Underlying command: `gh repo view <owner_repo> --json stargazersCount,forkCount,watchers,openIssues,pullRequests,diskUsage,createdAt,updatedAt,pushedAt`
- Output: `dict` → `{ "stars": int, "forks": int, "watchers": int, "open_issues": int, "open_prs": int, "size_kb": int, "created_at": str, "updated_at": str, "pushed_at": str }`
- Guardrail: read-only.

**2. `get_contributors`** — *MVP*
- Description: Top contributors ranked by commit count.
- Input: `owner_repo: str`, `limit: int = 10`
- Underlying command: `gh api repos/<owner_repo>/contributors`
- Output: `dict` → `{ "contributors": list[{"username": str, "contributions": int}] }`
- Guardrail: read-only, GitHub API rate-limit aware (respect `X-RateLimit-Remaining` header, surface a clear error if exhausted).

**3. `get_language_breakdown`** — *MVP*
- Description: Language usage percentages (e.g. 70% Python, 20% JS, 10% Shell).
- Input: `owner_repo: str`
- Underlying command: `gh api repos/<owner_repo>/languages`
- Output: `dict` → `{ "languages": { "Python": 70.2, "JavaScript": 20.1, "Shell": 9.7 } }` (raw byte counts converted to percentages)
- Guardrail: read-only.

**4. `get_topics`** — *MVP*
- Description: Repo topics/tags (e.g. `mcp`, `llm`, `agents`).
- Input: `owner_repo: str`
- Underlying command: `gh repo view <owner_repo> --json repositoryTopics`
- Output: `dict` → `{ "topics": list[str] }`
- Guardrail: read-only.

**5. `get_license`** — *MVP*
- Description: License type (MIT, Apache-2.0, GPL-3.0, etc.), or `null` if unlicensed.
- Input: `owner_repo: str`
- Underlying command: `gh repo view <owner_repo> --json licenseInfo`
- Output: `dict` → `{ "license": str | None }`
- Guardrail: read-only.

**6. `get_releases`** — *MVP*
- Description: Latest release plus recent release/tag history.
- Input: `owner_repo: str`, `limit: int = 5`
- Underlying command: `gh release list --repo <owner_repo> --limit <limit>`
- Output: `dict` → `{ "releases": list[{"tag": str, "name": str, "published_at": str}] }`
- Guardrail: read-only; if repo has no releases, return empty list, not an error.

**7. `get_default_branch_protection`** — *Stretch*
- Description: Whether the default branch has protection rules (maturity signal — is this a serious, well-maintained repo?).
- Input: `owner_repo: str`
- Underlying command: `gh api repos/<owner_repo>/branches/<default_branch>/protection`
- Output: `dict` → `{ "protected": bool, "details": dict | None }`
- Guardrail: read-only; **gracefully handle 403/404** — most public repos won't expose this without admin/write access, so treat that as `{"protected": "unknown"}` rather than a hard error.

**8. `get_commit_activity`** — *Stretch*
- Description: Weekly commit counts for the last year — shows whether a repo is actively maintained or effectively dead.
- Input: `owner_repo: str`
- Underlying command: `gh api repos/<owner_repo>/stats/commit_activity`
- Output: `dict` → `{ "weekly_commits": list[int], "total_last_year": int }`
- Guardrail: read-only; GitHub computes these stats async — if the API returns 202 (still computing), retry once after a short delay, else return a clear "stats not ready yet" message instead of hanging.

**9. `get_network_info`** — *Stretch*
- Description: Fork network — list of forks with owner and star count of each, to see how the project has spread.
- Input: `owner_repo: str`, `limit: int = 10`
- Underlying command: `gh api repos/<owner_repo>/forks`
- Output: `dict` → `{ "forks": list[{"owner": str, "stars": int, "url": str}] }`
- Guardrail: read-only.

### 🧩 Composite Summary

**10. `generate_repo_summary`** — *MVP*
- Description: The "cool" one-shot tool. Orchestrates `get_repo_stats` + `get_contributors` + `get_language_breakdown` + `get_topics` + `get_license` + `get_releases` + `summarize_readme` (from Discovery group) into a single combined "repo card" object. Makes no new subprocess/API calls of its own — pure aggregation.
- Input: `owner_repo: str`
- Output: `dict` → `{ "stats": {...}, "contributors": [...], "languages": {...}, "topics": [...], "license": str, "latest_release": {...}, "readme_summary_text": str }`
- Guardrail: none additional — inherits guardrails of the tools it calls; if one sub-call fails (e.g. no releases, or protection check 403s), it should degrade gracefully and return partial data with a `"warnings": list[str]` field rather than failing the whole summary.

### 🔍 Discovery

**11. `search_repos`** — *MVP*
- Description: Search GitHub for repositories matching a keyword or topic.
- Input: `query: str`, `limit: int = 5`
- Underlying command: `gh search repos <query> --limit <limit> --json fullName,description,stargazersCount,url`
- Output: `list[dict]` → `[{ "full_name": str, "description": str, "stars": int, "url": str }]`
- Guardrail: read-only, no side effects.

**12. `get_repo_info`** — *MVP*
- Description: Fetch metadata for a specific repo (quick-glance version; use `get_repo_stats` / `generate_repo_summary` for the fuller picture).
- Input: `owner_repo: str` (format `"owner/repo"`)
- Underlying command: `gh repo view <owner_repo> --json description,stargazersCount,defaultBranchRef,openIssues,pullRequests,licenseInfo`
- Output: `dict` → `{ "description": str, "stars": int, "default_branch": str, "open_issues": int, "open_prs": int, "license": str }`
- Guardrail: read-only.

**13. `summarize_readme`** — *MVP*
- Description: Read the repo's README and produce a natural-language summary. The one tool where the LLM itself does the "thinking" — everything else is deterministic tool-calling.
- Input: `owner_repo: str`
- Behavior: if not yet cloned, fetch README via `gh repo view <owner_repo> --json readmeText` (no clone needed just for this); return raw README text truncated to a safe token length; the calling LLM summarizes it in its response (the tool itself just returns text, it does not call another LLM internally — keep it simple).
- Output: `dict` → `{ "readme_text": str, "truncated": bool }`
- Guardrail: read-only.

### 📥 Setup

**14. `clone_repo`** — *MVP*
- Description: Clone a repo into the sandboxed workspace folder.
- Input: `owner_repo: str`
- Behavior: computes `dest = WORKSPACE_ROOT / repo_dir_name(owner_repo)`; if already exists, return existing path instead of re-cloning; else `git clone https://github.com/<owner_repo>.git <dest>`.
- Output: `dict` → `{ "repo_path": str, "already_existed": bool }`
- Guardrail: destination path always validated inside `WORKSPACE_ROOT`.

**15. `pull_latest`** — *MVP*
- Description: Pull latest changes for an already-cloned repo.
- Input: `repo_path: str`
- Underlying command: `git pull`
- Output: `dict` → `{ "output": str, "success": bool }`
- Guardrail: `repo_path` validated via `resolve_repo_path`.

### 🌿 Branches & History

**16. `list_branches`** — *MVP*
- Description: List all local and remote branches.
- Input: `repo_path: str`
- Underlying command: `git branch -a`
- Output: `dict` → `{ "branches": list[str], "current": str }`

**17. `checkout_branch`** — *MVP*
- Description: Switch to a branch, optionally creating it if it doesn't exist.
- Input: `repo_path: str`, `branch: str`, `create_new: bool = False`
- Underlying command: `git checkout <branch>` or `git checkout -b <branch>` if `create_new`
- Output: `dict` → `{ "success": bool, "message": str }`
- Guardrail: branch name sanitized (alphanumeric, `-`, `_`, `/` only — reject shell metacharacters).

**18. `list_commits`** — *MVP*
- Description: Show the last N commits.
- Input: `repo_path: str`, `n: int = 10`
- Underlying command: `git log -n <n> --pretty=format:"%H|%an|%ad|%s" --date=short`
- Output: `dict` → `{ "commits": list[{"hash": str, "author": str, "date": str, "message": str}] }`

**19. `get_file_history`** — *Stretch*
- Description: Show commit history for a specific file.
- Input: `repo_path: str`, `filepath: str`
- Underlying command: `git log --follow --pretty=format:"%H|%an|%ad|%s" --date=short -- <filepath>`
- Output: same shape as `list_commits`.
- Guardrail: `filepath` must resolve inside `repo_path` (no `../` traversal).

### 🔀 Comparison & Review

**20. `get_status`** — *MVP*
- Description: Show current working tree status.
- Input: `repo_path: str`
- Underlying command: `git status --short`
- Output: `dict` → `{ "staged": list[str], "unstaged": list[str], "untracked": list[str] }`

**21. `get_diff`** — *MVP*
- Description: Show diff between two branches or commits.
- Input: `repo_path: str`, `base: str`, `head: str`
- Underlying command: `git diff <base>..<head>`
- Output: `dict` → `{ "diff_text": str, "files_changed": int }`

**22. `compare_branches`** — *Stretch*
- Description: Show ahead/behind commit counts between two branches.
- Input: `repo_path: str`, `branch_a: str`, `branch_b: str`
- Underlying command: `git rev-list --left-right --count <branch_a>...<branch_b>`
- Output: `dict` → `{ "ahead": int, "behind": int }`

### 🔧 Issues & PRs

**23. `list_open_issues`** — *MVP*
- Description: List open issues, optionally filtered by label.
- Input: `owner_repo: str`, `label: str | None = None`
- Underlying command: `gh issue list --repo <owner_repo> --state open --json number,title,labels,createdAt` (+ `--label <label>` if provided)
- Output: `dict` → `{ "issues": list[{"number": int, "title": str, "labels": list[str], "created_at": str}] }`

**24. `list_pull_requests`** — *MVP* *(also covers `get_pr_diff` as a sub-action — see note)*
- Description: List open PRs with their CI check status.
- Input: `owner_repo: str`
- Underlying command: `gh pr list --repo <owner_repo> --json number,title,statusCheckRollup,author`
- Output: `dict` → `{ "prs": list[{"number": int, "title": str, "checks_status": str, "author": str}] }`

**25. `get_pr_diff`** — *MVP*
- Description: Show the code diff for a specific PR.
- Input: `owner_repo: str`, `pr_number: int`
- Underlying command: `gh pr diff <pr_number> --repo <owner_repo>`
- Output: `dict` → `{ "diff_text": str }`

> **Tool count reconciliation:** counting every group gives **25 tools total** — **20 MVP** (build & demo these) + **5 Stretch** (`get_default_branch_protection`, `get_commit_activity`, `get_network_info`, `get_file_history`, `compare_branches`). The "24" mentioned earlier in this doc was an estimate before the final count-through; 25 is the accurate number — close enough that it doesn't change the plan, just correcting the figure here.

---

## 8. Error Handling Convention

Every tool returns a consistent envelope so the LLM can reason about failures:

```python
{
  "ok": bool,
  "data": {...} | None,
  "error": str | None
}
```

Wrapper-level exceptions to handle explicitly:
- `PermissionError` → blocked/destructive command attempted
- `ValueError` → path escaped sandbox
- `subprocess.TimeoutExpired` → command took too long (30s default cap)
- `FileNotFoundError` → repo not cloned yet / git or gh not installed

---

## 9. Setup Instructions (for README later)

```bash
# Prerequisites
git --version
gh --version
gh auth login          # one-time, uses local browser/token flow

# Install
git clone <this-repo>
cd github-ops-mcp
pip install -e .

# Run — stdio mode (for Claude Desktop)
python -m github_ops_mcp.server --stdio

# Run — HTTP mode (remote/demo)
python -m github_ops_mcp.server --http --host 0.0.0.0 --port 8000
```

---

## 10. Demo Script (for interview / viva)

1. "Search for repositories about MCP servers" → `search_repos`
2. "Give me a full summary of the top result" → `generate_repo_summary` (this is the standout moment — one call surfaces stats, contributors, languages, topics, license, latest release, and README summary together)
3. "Who are the top contributors?" → `get_contributors`
4. "Clone it" → `clone_repo`
5. "What branches does it have?" → `list_branches`
6. "Show me the last 5 commits" → `list_commits`
7. "Any open issues labeled bug?" → `list_open_issues`
8. "Show me the diff on PR #12" → `get_pr_diff`

This sequence demonstrates all five tool groups (including the new Repo Stats & Insights group) in under 2 minutes — good for a live viva demo, and `generate_repo_summary` is the moment that makes the project feel "cool" rather than a plain CRUD wrapper.

---

## 11. Build Order (suggested)

1. `sandbox.py` + `config.py` + `validators.py` — get path safety and `owner_repo` validation right first
2. `git_wrapper.py` + `gh_wrapper.py` — wrappers with whitelist enforcement
3. `tools/discovery.py` (3 tools) — easiest, no filesystem writes
4. `tools/repo_stats.py` (6 MVP tools: stats, contributors, languages, topics, license, releases)
5. `tools/repo_summary.py` (1 tool: `generate_repo_summary`, built on top of #3 and #4 — do this once those are working)
6. `tools/setup.py` (2 tools) — clone/pull, test sandboxing here
7. `tools/branches.py` (MVP: list_branches, checkout_branch, list_commits; stretch: get_file_history)
8. `tools/comparison.py` (MVP: get_status, get_diff; stretch: compare_branches)
9. `tools/issues_prs.py` (3 tools: list_open_issues, list_pull_requests, get_pr_diff)
10. `tools/repo_stats_ext.py` (stretch only: branch protection, commit activity, network info) — skip until MVP is fully demoable
11. `server.py` — wire everything, add `--stdio`/`--http` flags
12. Test both transports manually
13. Write README + record demo GIF

---

## 12. Additional Nice-to-Haves (beyond the 5 tool-level stretch items in §7)

These are process/engineering extras, not new tools — add only after all 20 MVP tools + demo script are working:

- Cache `search_repos` and `generate_repo_summary` results for ~5 min to avoid hitting GitHub API rate limits (especially important since `generate_repo_summary` fans out into ~7 API calls internally)
- Add a `list_all_tools` meta-tool that just returns this table (nice for demo — "ask me what I can do")
- Simple pytest suite mocking `subprocess.run` to test wrapper guardrails without needing real git/gh calls
- Handle GitHub API rate-limit errors (HTTP 403 with `X-RateLimit-Remaining: 0`) with a clear, friendly error message across all `gh api`-based tools, since the Repo Stats & Insights group makes noticeably more API calls than the rest of the server combined