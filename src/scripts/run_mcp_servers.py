import os
import signal
import sys
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
from src.agent_tools.mcp_manager import MCPManager


def main() -> int:
    manager = MCPManager(enabled=True, autostart=True)

    def _shutdown(*_args) -> None:
        manager.stop_local_servers()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        while True:
            time.sleep(0.25)
    except KeyboardInterrupt:
        manager.stop_local_servers()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
