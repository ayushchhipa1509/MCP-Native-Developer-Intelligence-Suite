"""Entry point for the MCP Developer Intelligence Suite server.

Launches the 'developer-intel-suite' MCP server over stdio transport,
enabling communication with any MCP-compliant host (Claude Desktop,
custom CLI wrappers, or LangGraph orchestrators).
"""

from __future__ import annotations

import asyncio
import logging
import sys

from mcp.server.stdio import stdio_server

from mcp_server.server import create_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    stream=sys.stderr,  # Keep logs on stderr; stdout is for JSON-RPC
)
logger = logging.getLogger(__name__)


async def serve() -> None:
    """Initialize and run the MCP server over stdio transport."""
    server = create_server()
    logger.info("Starting developer-intel-suite MCP server (stdio transport)")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    """Synchronous entry point for the mcp-dev-intel CLI command."""
    asyncio.run(serve())


if __name__ == "__main__":
    main()
