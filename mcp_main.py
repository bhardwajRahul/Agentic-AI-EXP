"""
Main entry point to run the unified MCP server with all Google service tools.
"""

import sys
from pathlib import Path

root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

from MCP.core.server import server
import MCP.tools.gmail_tools
import MCP.tools.calendar_tools
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.info("📦 MCP tools...")

    server.run()
