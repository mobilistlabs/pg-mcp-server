# server/tools/connection.py
from server.config import mcp
from server.logging_config import get_logger

logger = get_logger("pg-mcp.tools.connection")

def register_connection_tools():
    """Register the database connection tools with the MCP server."""
    logger.debug("Registering database connection tools")

    @mcp.tool()
    async def list_connections():
        """
        List all available database connections registered at server startup.

        Returns:
            List of available connection IDs and their database names.
            Use these conn_id values with pg_query and other tools.
        """
        db = mcp.state["db"]
        connections = []
        for conn_id, connection_string in db._connection_map.items():
            # Extract only the database name from the URL — never expose credentials
            try:
                import urllib.parse
                parsed = urllib.parse.urlparse(connection_string)
                db_name = parsed.path.lstrip("/")
                host = parsed.hostname or "unknown"
            except Exception:
                db_name = "unknown"
                host = "unknown"
            connections.append({"conn_id": conn_id, "database": db_name, "host": host})
        logger.info(f"Listed {len(connections)} registered connections")
        return connections