# MCP Servers

Model Context Protocol servers for extending agent capabilities.

## Structure

Each subdirectory is a standalone MCP server:
- `threejs/` - 3D visualization MCP server with React widgets
- `open_memory/` - Persistent memory MCP server (git submodule)

## Current Servers

### threejs

**Purpose**: Interactive 3D visualizations for data and generative UI

**Features**:
- React-based Three.js widgets
- HTTP transport for agent integration
- Server-side rendering support

**Port**: 3108

**Usage in Agents**:
```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    "threejs": {
        "transport": "http",
        "url": "http://localhost:3108/mcp"
    }
})
tools = await client.get_tools()
```

### open_memory

**Purpose**: Persistent memory and context storage for agents using Gemini embeddings

**Features**:
- SQLite-based storage (metadata + vectors)
- Gemini embeddings for semantic search
- MCP server for agent integration
- Persistent memory across sessions

**Port**: 8080

**Usage in Agents**:
```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    "openmemory": {
        "transport": "http",
        "url": "http://localhost:8080/mcp"
    }
})
tools = await client.get_tools()
```

**Configuration** (via docker-compose.yml):
- `GEMINI_API_KEY` - Required for embeddings
- `OM_TIER=smart` - Use smart embedding mode
- `OM_EMBEDDINGS=gemini` - Use Gemini for embeddings
- `OM_DB_PATH=/data/openmemory.sqlite` - Database location

## Adding New MCP Server

1. Create new directory (e.g., `mcp/database/`)
2. Implement MCP server following the protocol:
   - Define tools with schemas
   - Implement HTTP transport
   - Add health check endpoint
3. Add to agent's MCP client configuration
4. Update `docker-compose.yml` if needed
5. Document in this README

## Example: Database MCP Server

```
mcp/database/
├── server.ts          # MCP server implementation
├── tools/             # Database query tools
│   ├── query.ts
│   └── schema.ts
├── package.json
└── README.md
```

## MCP Resources

- [MCP Documentation](https://modelcontextprotocol.io/)
- [MCP TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
