import os
import sys

from dotenv import load_dotenv

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


load_dotenv()

AVAILABLE_MCP_SERVER_URL = "http://localhost:8300/mcp"