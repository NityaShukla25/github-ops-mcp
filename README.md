# github-ops-mcp

A small MCP server that lets an LLM (Claude Desktop, Claude Code, or any MCP client) search GitHub, clone repos into a sandboxed workspace, and run common read-only `git` / `gh` operations. Personal project — see `plan.md` for the design.

## 1. Prerequisites

Make sure these are installed and working before you continue:

```bash
git --version           # any recent git
gh --version            # GitHub CLI — https://cli.github.com/
python3 --version       # Python 3.11 or newer
```

Log in to GitHub once (opens a browser):

```bash
gh auth login
```

Verify:

```bash
gh auth status
```

## 2. Install

```bash
git clone <this-repo> github_operation_mcp
cd github_operation_mcp

# Create a virtualenv (any Python 3.11+ works; example uses 3.14)
python3 -m venv .venv
source .venv/bin/activate

# Install the package + its one dependency (mcp SDK, pinned to v1.x)
pip install --upgrade pip
pip install -e .
```

## 3. Run the server

### Option A — stdio (for Claude Desktop / Claude Code)

```bash
python -m github_ops_mcp.server --stdio
```

You normally don't run this by hand — Claude Desktop launches it for you via the config in step 4.

### Option B — HTTP / SSE (for remote clients / demos)

```bash
python -m github_ops_mcp.server --http --host 0.0.0.0 --port 8000
```

The MCP endpoint is then at `http://<host>:8000/mcp`.

## 4. Wire it into Claude Desktop

Edit (or create) the config file:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

Add this entry (replace the two paths with your absolute paths):

```json
{
  "mcpServers": {
    "github-ops": {
      "command": "/Users/YOU/Documents/github_operation_mcp/.venv/bin/python",
      "args": ["-m", "github_ops_mcp.server", "--stdio"],
      "env": {
        "WORKSPACE_ROOT": "/Users/YOU/Documents/github_operation_mcp/test_repos"
      }
    }
  }
}
```

Then **fully quit Claude Desktop (Cmd+Q, not just close the window)** and reopen it. You should see 25 tools appear under the `github-ops` server.

> **`WORKSPACE_ROOT`** — optional. Every `clone_repo` call lands under this directory as `<owner>__<repo>/`. If you omit it, the server defaults to a `workspace/` folder next to the package.

## 5. Wire it into Claude Code

Either add the same block to a `.mcp.json` at the project root, or run:

```bash
claude mcp add github-ops \
  /Users/YOU/Documents/github_operation_mcp/.venv/bin/python \
  -- -m github_ops_mcp.server --stdio
```

## 6. Try it

In Claude Desktop:

1. *"Search for repositories about MCP servers"* → `search_repos`
2. *"Give me a full summary of `modelcontextprotocol/python-sdk`"* → `generate_repo_summary`
3. *"Clone `octocat/Hello-World`"* → `clone_repo`
4. *"What branches does it have?"* → `list_branches`
5. *"Show me the last 5 commits"* → `list_commits`
6. *"Any open PRs on `facebook/react`?"* → `list_pull_requests`

## Tools (25)

- **Discovery** — `search_repos`, `get_repo_info`, `summarize_readme`
- **Repo stats** — `get_repo_stats`, `get_contributors`, `get_language_breakdown`, `get_topics`, `get_license`, `get_releases`
- **Stretch stats** — `get_default_branch_protection`, `get_commit_activity`, `get_network_info`
- **Composite** — `generate_repo_summary`
- **Setup** — `clone_repo`, `pull_latest`
- **Branches** — `list_branches`, `checkout_branch`, `list_commits`, `get_file_history`
- **Comparison** — `get_status`, `get_diff`, `compare_branches`
- **Issues & PRs** — `list_open_issues`, `list_pull_requests`, `get_pr_diff`

Every tool returns `{ ok: bool, data: ..., error: ... }`.

## Safety

- All clones live under `WORKSPACE_ROOT` (`./workspace/` by default). Path traversal (`../`) is blocked.
- `git` and `gh` subcommands are whitelisted. Destructive commands (`push`, `reset --hard`, `rebase`, `clean`, `branch -D`, `gh repo delete/edit`, …) raise `PermissionError`.
- `gh api` calls are restricted to `repos/...` endpoints.
- User inputs are passed as argv items, never shell-interpolated (`shell=False`).
- Auth is *not* handled by this server — it relies on your existing `gh auth login` session and git credentials.

## Troubleshooting

- **Claude Desktop log shows `Read-only file system: '/workspace'`** — you're on an older build; pull latest, the default workspace now anchors to the package directory instead of the CWD.
- **Every tool call errors with `unexpected keyword argument 'args'`** — you're on an older build; `functools.wraps` is now used so FastMCP sees the real parameter names. Pull latest.
- **`gh: To get started with GitHub CLI, please run: gh auth login`** — run `gh auth login` from a terminal, then restart Claude Desktop.
- **Server doesn't appear in Claude Desktop** — check the log at `~/Library/Logs/Claude/mcp-server-github-ops.log`. Common issues: wrong Python path in the config, virtualenv not activated when you ran `pip install -e .`.

## Layout

```
github_operation_mcp/
├── pyproject.toml
├── README.md
├── plan.md
├── test_repos/                 # cloned repos land here (gitignored)
└── src/github_ops_mcp/
    ├── server.py               # FastMCP app + --stdio/--http entrypoint
    ├── config.py               # WORKSPACE_ROOT, timeouts
    ├── validators.py           # owner_repo + branch name checks
    ├── sandbox.py              # path resolution + traversal guard
    ├── git_wrapper.py          # git subprocess wrapper (whitelist)
    ├── gh_wrapper.py           # gh subprocess wrapper (whitelist)
    └── tools/
        ├── discovery.py
        ├── setup.py
        ├── branches.py
        ├── comparison.py
        ├── issues_prs.py
        ├── repo_stats.py
        ├── repo_stats_ext.py
        └── repo_summary.py
```
