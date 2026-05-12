# PostgreSQL Model Context Protocol (PG-MCP) Server

A Model Context Protocol (MCP) server for PostgreSQL databases with enhanced capabilities for AI agents.

More info on the pg-mcp project here:
### [https://stuzero.github.io/pg-mcp/](https://stuzero.github.io/pg-mcp/)

## Overview

PG-MCP is a server implementation of the [Model Context Protocol](https://modelcontextprotocol.io) for PostgreSQL databases. It provides a comprehensive API for AI agents to discover, connect to, query, and understand PostgreSQL databases through MCP's resource-oriented architecture.

This implementation builds upon and extends the [reference Postgres MCP implementation](https://github.com/modelcontextprotocol/servers/tree/main/src/postgres) with several key enhancements:

1. **Full Server Implementation**: Built as a complete server with SSE transport for production use
2. **Multi-database Support**: Connect to multiple PostgreSQL databases simultaneously
3. **Rich Catalog Information**: Extracts and exposes table/column descriptions from the database catalog
4. **Extension Context**: Provides detailed YAML-based knowledge about PostgreSQL extensions like PostGIS and pgvector
5. **Query Explanation**: Includes a dedicated tool for analyzing query execution plans
6. **Robust Connection Management**: Proper lifecycle for database connections with secure connection ID handling

## Features

### Connection Management

- **Connect Tool**: Register PostgreSQL connection strings and get a secure connection ID
- **Disconnect Tool**: Explicitly close database connections when done
- **Connection Pooling**: Efficient connection management with pooling

### Query Tools

- **pg_query**: Execute read-only SQL queries using a connection ID
- **pg_explain**: Analyze query execution plans in JSON format

### Schema Discovery Resources

- List schemas with descriptions
- List tables with descriptions and row counts
- Get column details with data types and descriptions
- View table constraints and indexes
- Explore database extensions

### Data Access Resources

- Sample table data (with pagination)
- Get approximate row counts

### Extension Context

Built-in contextual information for PostgreSQL extensions like:

- **PostGIS**: Spatial data types, functions, and examples
- **pgvector**: Vector similarity search functions and best practices

Additional extensions can be easily added via YAML config files.

## Installation

### Prerequisites

- Python 3.13+
- PostgreSQL database(s)

### Using Docker

Pull and run the image from Docker Hub:

```bash
docker run -d --name pg-mcp -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/mydb \
  ufuf/pg-mcp:latest
```

The server is then reachable at `http://localhost:8000/sse`.

#### Connection environment variables

On startup the server auto-registers every PostgreSQL connection it finds in the environment. You can pass connections in two ways (mix freely):

| Variable                       | Purpose                                            |
| ------------------------------ | -------------------------------------------------- |
| `DATABASE_URL`                 | Primary / default connection                       |
| `POSTGRES_<NAME>_URL`          | Any number of additional named connections         |

Examples:

```bash
DATABASE_URL=postgresql://user:pass@host:5432/mydb
POSTGRES_BILLING_URL=postgresql://user:pass@host:5432/billing
POSTGRES_ANALYTICS_URL=postgresql://user:pass@host:5432/analytics
```

Each variable is registered with the global database manager and a connection UUID is logged at startup — clients use that UUID for subsequent queries. If none of these variables are set, the server still starts but clients must register a connection at runtime via the MCP `connect` tool, and a prominent warning is printed to the logs.

#### Docker Compose

```bash
git clone https://github.com/mobilistlabs/pg-mcp-server.git
cd pg-mcp-server

# Put your DATABASE_URL / POSTGRES_*_URL values in a .env file
cp .env.example .env
$EDITOR .env

docker compose up -d
```

`docker-compose.yml` reads the `.env` file automatically. Logs (`docker logs pg-mcp`) will show one `Auto-registered connection from <VAR>: <uuid>` line per detected variable.

### Manual Installation

```bash
# Clone the repository
git clone https://github.com/stuzero/pg-mcp-server.git
cd pg-mcp-server

# Install dependencies and create a virtual environment ( .venv )
uv sync

# Activate the virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Run the server
python -m server.app
```

## Usage

### Testing the Server

The repository includes test scripts to verify server functionality:

```bash
# Basic server functionality test
python test.py "postgresql://username:password@hostname:port/database"

# Claude-powered natural language to SQL conversion
python example-clients/claude_cli.py "Show me the top 5 customers by total sales"
```

The `claude_cli.py` script requires environment variables:

```
# .env file
DATABASE_URL=postgresql://username:password@hostname:port/database
ANTHROPIC_API_KEY=your-anthropic-api-key
PG_MCP_URL=http://localhost:8000/sse
```



### For AI Agents

Example prompt for use with agents:

```
Use the PostgreSQL MCP server to analyze the database. 
Available tools:
- connect: Register a database connection string and get a connection ID
- disconnect: Close a database connection
- pg_query: Execute SQL queries using a connection ID
- pg_explain: Get query execution plans

You can explore schema resources via:
pgmcp://{conn_id}/schemas
pgmcp://{conn_id}/schemas/{schema}/tables
pgmcp://{conn_id}/schemas/{schema}/tables/{table}/columns

A comprehensive database description is available at this resource:
pgmcp://{conn_id}/
```

## Architecture

This server is built on:

- **MCP**: The Model Context Protocol foundation
- **FastMCP**: Python library for MCP
- **asyncpg**: Asynchronous PostgreSQL client
- **YAML**: For extension context information

## Security Considerations

- The server runs in read-only mode by default (enforced via transaction settings)
- Connection details are never exposed in resource URLs, only opaque connection IDs
- Database credentials only need to be sent once during the initial connection

## Contributing

Contributions are welcome! Areas for expansion:

- Additional PostgreSQL extension context files
- More schema introspection resources
- Query optimization suggestions
