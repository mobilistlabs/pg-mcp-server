# server/app.py
import os
import sys
from server.logging_config import configure_logging, get_logger, configure_uvicorn_logging

# Configure logging first thing to capture all subsequent log messages
log_level = os.environ.get("LOG_LEVEL", "INFO")
configure_logging(level=log_level)
logger = get_logger("app")

# Import MCP instance and other components after logging is configured
from server.config import mcp, global_db

# Import registration functions
from server.resources.schema import register_schema_resources
from server.resources.data import register_data_resources
from server.resources.extensions import register_extension_resources
from server.tools.connection import register_connection_tools
from server.tools.query import register_query_tools
from server.tools.viz import register_viz_tools
from server.prompts.natural_language import register_natural_language_prompts
from server.prompts.data_visualization import register_data_visualization_prompts

# Register tools and resources with the MCP server
logger.info("Registering resources and tools")
register_schema_resources()   # Schema-related resources (schemas, tables, columns)
register_extension_resources()
register_data_resources()     # Data-related resources (sample, rowcount, etc.)
register_connection_tools()   # Connection management tools
register_query_tools()
register_viz_tools()         # Visualization tools
register_natural_language_prompts()  # Natural language to SQL prompts
register_data_visualization_prompts() # Data visualization prompts


def register_env_connections():
    """Auto-register PostgreSQL connections from DATABASE_URL and POSTGRES_*_URL env vars."""
    registered = []

    primary = os.environ.get("DATABASE_URL")
    if primary:
        registered.append(("DATABASE_URL", global_db.register_connection(primary)))

    for key, value in sorted(os.environ.items()):
        if key == "DATABASE_URL":
            continue
        if key.startswith("POSTGRES_") and key.endswith("_URL") and value:
            registered.append((key, global_db.register_connection(value)))

    for label, conn_id in registered:
        logger.info(f"Auto-registered connection from {label}: {conn_id}")

    if not registered:
        bar = "=" * 78
        banner = (
            "\n" + bar + "\n"
            "  WARNING: no PostgreSQL connection env vars found.\n"
            "\n"
            "  Set DATABASE_URL so the server can auto-register the connection\n"
            "  at startup. Example:\n"
            "\n"
            "    docker run -p 8000:8000 \\\n"
            "      -e DATABASE_URL=postgresql://user:pass@host:5432/mydb \\\n"
            "      ufuf/pg-mcp:latest\n"
            "\n"
            "  Additional databases can be added with any number of\n"
            "  POSTGRES_<NAME>_URL=... env vars.\n"
            "\n"
            "  Or with docker compose, put the same vars in a .env file next to\n"
            "  docker-compose.yml.\n"
            "\n"
            "  Without these, the server will still start but clients must call the\n"
            "  MCP 'connect' tool with a connection string before any query works.\n"
            + bar + "\n"
        )
        print(banner, file=sys.stderr, flush=True)
        logger.warning("No PostgreSQL connection env vars found; see banner above")


register_env_connections()


from contextlib import asynccontextmanager
from starlette.applications import Starlette
from starlette.routing import Mount
import uvicorn

@asynccontextmanager
async def starlette_lifespan(app):
    logger.info("Starlette application starting up")
    yield
    logger.info("Starlette application shutting down, closing all database connections")
    await global_db.close()

if __name__ == "__main__":
    logger.info("Starting MCP server with SSE transport")
    app = Starlette(
        routes=[Mount('/', app=mcp.sse_app())],
        lifespan=starlette_lifespan
    )
    
    # Configure Uvicorn with our logging setup
    uvicorn_log_config = configure_uvicorn_logging(log_level)
    
    # Use our configured log level for Uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0",
        port=8000, 
        log_level=log_level.lower(),
        log_config=uvicorn_log_config
    )