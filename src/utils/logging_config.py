import logging
import os


def configure_logging():
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = logging.getLevelName(level_name)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Explicit MCP-related loggers
    logging.getLogger("fastmcp").setLevel(level)
    logging.getLogger("mcp").setLevel(level)

    # Silence noisy dependencies
    logging.getLogger("httpx").setLevel(logging.WARNING)
