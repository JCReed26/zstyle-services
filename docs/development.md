# Development Guide

## Setting up Development Environment

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

## Running Tests

```bash
pytest
```

## Adding New Agents

1. Create a new directory in `/agents/`
2. Follow the same structure as `exec_func_coach`
3. Define your agent with appropriate tools
4. Add tests in `/tests/`

## Adding New Services

1. Create service in `/services/` directory
2. Follow the same pattern as existing services
3. Use async SQLAlchemy for database operations
4. Add proper error handling

## MCP Integration

Model Context Protocol (MCP) allows agents to communicate with external tools.
To add new MCP capabilities:

1. Define new tools in appropriate agent
2. Implement MCP server for external service
3. Connect using McpToolset in agent configuration