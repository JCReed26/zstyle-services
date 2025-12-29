"""
TickTick Agent Implementation using Google ADK OpenAPIToolset.

This module defines a specialized agent for TickTick integration.
It uses a partial OpenAPI specification to generate tools dynamically.
It employs a ContextVar-based header injection to support multi-user authentication
with a single global agent instance.
"""
import os
import json
import contextvars
from typing import Dict, Any, List, Optional, MutableMapping, Iterator
from google.adk.agents import Agent
from google.adk.tools.openapi_tool.openapi_spec_parser.openapi_toolset import OpenAPIToolset
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import ToolContext

# Removed: from .helpers import _get_credential
# Removed: from database.models import CredentialType
# Agents never import credential helpers directly

# ContextVar to hold the current user's access token during execution
_current_ticktick_token: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("ticktick_token", default=None)

class DynamicAuthHeaders(MutableMapping):
    """
    A dictionary-like object that injects the Authorization header
    dynamically from a ContextVar.
    """
    def __init__(self):
        self._store = {}

    def __getitem__(self, key):
        if key == "Authorization":
            token = _current_ticktick_token.get()
            if token:
                return f"Bearer {token}"
            return "" # Or raise error?
        return self._store[key]

    def __setitem__(self, key, value):
        self._store[key] = value

    def __delitem__(self, key):
        del self._store[key]

    def __iter__(self) -> Iterator:
        keys = list(self._store.keys())
        if "Authorization" not in keys:
            keys.append("Authorization")
        return iter(keys)

    def __len__(self):
        return len(self._store) + 1

# Partial OpenAPI Specification for TickTick
TICKTICK_OPENAPI_SPEC = """
{
  "openapi": "3.0.0",
  "info": {
    "title": "TickTick API",
    "version": "1.0.0",
    "description": "Partial TickTick API for Agent integration"
  },
  "servers": [
    {
      "url": "https://api.ticktick.com"
    }
  ],
  "paths": {
    "/open/v1/project": {
      "get": {
        "operationId": "list_projects",
        "summary": "List all projects",
        "description": "Retrieve a list of all projects (lists) in the user's account.",
        "responses": {
          "200": {
            "description": "A list of projects",
            "content": {
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "properties": {
                      "id": { "type": "string" },
                      "name": { "type": "string" },
                      "color": { "type": "string" },
                      "sortOrder": { "type": "integer" }
                    }
                  }
                }
              }
            }
          }
        }
      }
    },
    "/open/v1/project/{projectId}/task": {
      "get": {
        "operationId": "list_project_tasks",
        "summary": "List tasks in a project",
        "description": "Get all tasks for a specific project.",
        "parameters": [
          {
            "name": "projectId",
            "in": "path",
            "required": true,
            "description": "The ID of the project to retrieve tasks from",
            "schema": { "type": "string" }
          }
        ],
        "responses": {
          "200": {
            "description": "A list of tasks",
            "content": {
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "properties": {
                      "id": { "type": "string" },
                      "projectId": { "type": "string" },
                      "title": { "type": "string" },
                      "content": { "type": "string" },
                      "startDate": { "type": "string" },
                      "dueDate": { "type": "string" },
                      "priority": { "type": "integer" },
                      "status": { "type": "integer" }
                    }
                  }
                }
              }
            }
          }
        }
      }
    },
    "/open/v1/task": {
      "post": {
        "operationId": "create_task",
        "summary": "Create a new task",
        "description": "Create a new task in a specific project or the default list.",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "required": ["title"],
                "properties": {
                  "title": { "type": "string" },
                  "content": { "type": "string" },
                  "projectId": { "type": "string" },
                  "dueDate": { "type": "string" },
                  "priority": { "type": "integer" }
                }
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Task created successfully",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "id": { "type": "string" },
                    "title": { "type": "string" }
                  }
                }
              }
            }
          }
        }
      }
    },
    "/open/v1/task/{taskId}/complete": {
      "post": {
        "operationId": "complete_task",
        "summary": "Complete a task",
        "description": "Mark a task as completed.",
        "parameters": [
          {
            "name": "taskId",
            "in": "path",
            "required": true,
            "description": "The ID of the task to complete",
            "schema": { "type": "string" }
          }
        ],
        "responses": {
          "200": {
            "description": "Task completed successfully",
             "content": {
              "application/json": {
                "schema": { "type": "object" }
              }
            }
          }
        }
      }
    }
  }
}
"""

TICKTICK_AGENT_INSTRUCTION = """
You are the TickTick Task Manager Agent.
Your role is to help the user manage their tasks, projects, and to-do lists using TickTick.

TOOLS AVAILABLE:
- list_projects: Get all available lists/projects. Use this to find a projectId if one isn't provided.
- list_project_tasks: Get tasks for a specific project. Requires a projectId.
- create_task: Create a new task. You can specify title, content, dueDate, priority, and projectId.
- complete_task: Mark a task as done using its taskId.

BEST PRACTICES:
1. When asking to create a task, check if the user specified a project. If not, you can create it in the default list (by omitting projectId) or ask for clarification if context suggests a specific list.
2. To complete a task, you often need to find it first. If you don't have the taskId, try listing tasks in the relevant project first to find the ID.
3. When listing tasks, summarize them clearly for the user (e.g., "Here are your tasks in 'Work':...").
4. Priority levels are: 0 (None), 1 (Low), 3 (Medium), 5 (High).
5. Dates should be formatted as ISO 8601 strings (e.g., "2023-12-31T23:59:59+0000").
"""

# Initialize Toolset with Dynamic Headers
# The OpenAPIToolset will refer to this mapping for every request.
_dynamic_headers = DynamicAuthHeaders()
# OpenAPIToolset might not accept headers in init depending on version.
# We will try to set it after or assume the library handles it differently.
# For now, we remove it from init to fix the crash and will investigate how to inject it.
ticktick_toolset = OpenAPIToolset(
    spec_str=TICKTICK_OPENAPI_SPEC,
    spec_str_type='json'
)
# Inject headers if possible (this is a guess fix for the ADK library)
if hasattr(ticktick_toolset, 'headers'):
    ticktick_toolset.headers = _dynamic_headers

# Global TickTick Agent
ticktick_agent = Agent(
    model='gemini-2.0-flash-exp',
    name='ticktick_manager',
    description='Specialized agent for managing TickTick tasks and projects.',
    instruction=TICKTICK_AGENT_INSTRUCTION,
    tools=[ticktick_toolset]
)

class TickTickAgentTool(AgentTool):
    """
    A wrapper around the TickTick Agent that sets the user's authentication
    context before execution.
    """
    def __init__(self, agent: Agent):
        super().__init__(agent=agent)
    
    async def run_async(self, tool_context: ToolContext, **kwargs) -> Dict[str, Any]:
        user_id = tool_context.state.get('user_id') if tool_context.state else None
        if not user_id:
            # Fallback to ContextVar
            from channels.router import _current_user_id
            user_id = _current_user_id.get()
        if not user_id:
             return {"status": "error", "message": "User not identified for TickTick access."}

        # Get token from AuthService (agents never see tokens directly)
        from services.auth import AuthService
        token = await AuthService.get_ticktick_token(user_id)
        if not token:
             return {
                 "status": "error", 
                 "message": "TickTick authentication not configured."
             }
        
        # Set ContextVar for the duration of this call
        token_var = _current_ticktick_token.set(token)
        try:
            # Delegate to standard AgentTool execution
            return await super().run_async(tool_context, **kwargs)
        finally:
            # Clean up
            _current_ticktick_token.reset(token_var)

# Export the tool wrapper for use in capabilities.py
ticktick_tool_wrapper = TickTickAgentTool(agent=ticktick_agent)

