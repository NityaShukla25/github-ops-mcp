import os
from pathlib import Path

# Default workspace lives next to the package, so it works no matter where the
# server is launched from (e.g. Claude Desktop launches it with cwd=/).
_DEFAULT_WORKSPACE = Path(__file__).resolve().parents[2] / "workspace"

WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT") or _DEFAULT_WORKSPACE).resolve()
WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)

CMD_TIMEOUT = 30
README_TRUNCATE_CHARS = 8000
