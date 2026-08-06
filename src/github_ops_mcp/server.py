import argparse

from mcp.server.fastmcp import FastMCP

from .tools import branches, comparison, discovery, issues_prs, repo_stats, repo_stats_ext, repo_summary, setup

mcp = FastMCP("github-ops-mcp")

# --- Discovery ---
mcp.tool()(discovery.search_repos)
mcp.tool()(discovery.get_repo_info)
mcp.tool()(discovery.summarize_readme)

# --- Repo stats (MVP) ---
mcp.tool()(repo_stats.get_repo_stats)
mcp.tool()(repo_stats.get_contributors)
mcp.tool()(repo_stats.get_language_breakdown)
mcp.tool()(repo_stats.get_topics)
mcp.tool()(repo_stats.get_license)
mcp.tool()(repo_stats.get_releases)

# --- Repo stats (stretch) ---
mcp.tool()(repo_stats_ext.get_default_branch_protection)
mcp.tool()(repo_stats_ext.get_commit_activity)
mcp.tool()(repo_stats_ext.get_network_info)

# --- Composite ---
mcp.tool()(repo_summary.generate_repo_summary)

# --- Setup ---
mcp.tool()(setup.clone_repo)
mcp.tool()(setup.pull_latest)

# --- Branches ---
mcp.tool()(branches.list_branches)
mcp.tool()(branches.checkout_branch)
mcp.tool()(branches.list_commits)
mcp.tool()(branches.get_file_history)

# --- Comparison ---
mcp.tool()(comparison.get_status)
mcp.tool()(comparison.get_diff)
mcp.tool()(comparison.compare_branches)

# --- Issues & PRs ---
mcp.tool()(issues_prs.list_open_issues)
mcp.tool()(issues_prs.list_pull_requests)
mcp.tool()(issues_prs.get_pr_diff)


def main() -> None:
    parser = argparse.ArgumentParser(description="GitHub Ops MCP server")
    parser.add_argument("--stdio", action="store_true", help="Run over stdio (default)")
    parser.add_argument("--http", action="store_true", help="Run over streamable HTTP")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.http:
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
