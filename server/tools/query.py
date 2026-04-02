# server/tools/query.py
import re
from sqlglot import parse, exp
from server.config import mcp
from mcp.server.fastmcp import Context
from server.logging_config import get_logger

logger = get_logger("pg-mcp.tools.query")

# Allowed top-level SQL statement types (read-only)
ALLOWED_STATEMENT_TYPES = (
    exp.Select,
)

# SHOW parses as exp.Command — only allow SHOW among Command types
ALLOWED_COMMAND_NAMES = {"SHOW"}

# Regex to strip EXPLAIN prefix variants and extract the inner query
_EXPLAIN_PREFIX_RE = re.compile(
    r"EXPLAIN(?:\s+ANALYZE)?(?:\s+VERBOSE)?(?:\s*\([^)]*\))?\s+",
    re.IGNORECASE,
)


def validate_read_only(query: str) -> None:
    """
    Validate that the SQL query is read-only.
    Allows: SELECT, SHOW, EXPLAIN (of read-only queries).
    Blocks: INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, TRUNCATE,
            GRANT, REVOKE, COPY, SET, VACUUM, ANALYZE, DO, CALL, etc.

    Raises:
        ValueError: If the query contains write/DDL statements.
    """
    stripped = query.strip().upper()

    # Handle EXPLAIN variants: strip the prefix and validate the inner query
    if stripped.startswith("EXPLAIN"):
        inner_match = _EXPLAIN_PREFIX_RE.match(query.strip())
        if inner_match:
            inner_query = query.strip()[inner_match.end():]
            if not inner_query.strip():
                raise ValueError("EXPLAIN with empty inner query.")
            validate_read_only(inner_query)
            return
        raise ValueError("Could not parse EXPLAIN query.")

    try:
        statements = parse(query, dialect="postgres")
    except Exception as e:
        raise ValueError(f"SQL parse error: {e}")

    if not statements:
        raise ValueError("Empty SQL query.")

    for stmt in statements:
        if stmt is None:
            continue
        # Allow SHOW commands (parsed as exp.Command with this="SHOW")
        if isinstance(stmt, exp.Command):
            cmd_name = str(stmt.this).upper() if stmt.this else ""
            if cmd_name in ALLOWED_COMMAND_NAMES:
                continue
            raise ValueError(
                f"Only read-only queries are allowed. Got command: {cmd_name}"
            )
        if not isinstance(stmt, ALLOWED_STATEMENT_TYPES):
            stmt_type = type(stmt).__name__
            raise ValueError(
                f"Only read-only queries are allowed. Got: {stmt_type}"
            )


async def execute_query(query: str, conn_id: str, params=None, ctx=Context):
    """
    Execute a read-only SQL query against the PostgreSQL database.

    Args:
        query: The SQL query to execute (must be read-only)
        conn_id: Connection ID (required)
        params: Parameters for the query (optional)
        ctx: Optional request context

    Returns:
        Query results as a list of dictionaries
    """

    # Validate that the query is read-only before executing
    validate_read_only(query)

    db = mcp.state["db"]
    if not db:
        raise ValueError("Database connection not available in MCP state.")

    logger.info(f"Executing query on connection ID {conn_id}: {query}")

    async with db.get_connection(conn_id) as conn:
        # Ensure we're in read-only mode
        await conn.execute("SET TRANSACTION READ ONLY")

        # Execute the query
        try:
            records = await conn.fetch(query, *(params or []))
            return [dict(record) for record in records]
        except Exception as e:
            # Log the error but don't couple to specific error types
            logger.error(f"Query execution error: {e}")
            raise

def register_query_tools():
    """Register database query tools with the MCP server."""
    logger.debug("Registering query tools")
    
    @mcp.tool()
    async def pg_query(query: str, conn_id: str, params=None):
        """
        Execute a read-only SQL query against the PostgreSQL database.
        
        Args:
            query: The SQL query to execute (must be read-only)
            conn_id: Connection ID previously obtained from the connect tool
            params: Parameters for the query (optional)
            
        Returns:
            Query results as a list of dictionaries
        """
        # Execute the query using the connection ID 
        return await execute_query(query, conn_id, params)
        
    @mcp.tool()
    async def pg_explain(query: str, conn_id: str, params=None):
        """
        Execute an EXPLAIN (FORMAT JSON) query to get PostgreSQL execution plan.
        
        Args:
            query: The SQL query to analyze
            conn_id: Connection ID previously obtained from the connect tool
            params: Parameters for the query (optional)
            
        Returns:
            Complete JSON-formatted execution plan
        """
        # Prepend EXPLAIN to the query
        explain_query = f"EXPLAIN (FORMAT JSON) {query}"
        
        # Execute the explain query
        result = await execute_query(explain_query, conn_id, params)
        
        # Return the complete result
        return result