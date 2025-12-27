"""
TickTick Agent Implementation using Google ADK OpenAPIToolset.

This module defines a specialized agent for TickTick integration.
It uses a partial OpenAPI specification to generate tools dynamically.
"""
import os
import json
from typing import Dict, Any, List, Optional
from google.adk.agents import Agent
from google.adk.tools.openapi_tool.openapi_spec_parser.openapi_toolset import OpenAPIToolset
from .helpers import _get_credential
from database.models import CredentialType

# Partial OpenAPI Specification for TickTick
# Based on common endpoints needed for task management
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
                      "id": { "type": "string", "description": "The project ID" },
                      "name": { "type": "string", "description": "The name of the project" },
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
                      "id": { "type": "string", "description": "Task ID" },
                      "projectId": { "type": "string", "description": "Project ID" },
                      "title": { "type": "string", "description": "Task title" },
                      "content": { "type": "string", "description": "Task description/content" },
                      "startDate": { "type": "string", "format": "date-time" },
                      "dueDate": { "type": "string", "format": "date-time" },
                      "timeZone": { "type": "string" },
                      "isAllDay": { "type": "boolean" },
                      "priority": { "type": "integer", "description": "0: None, 1: Low, 3: Medium, 5: High" },
                      "status": { "type": "integer", "description": "0: Normal, 2: Completed" },
                      "completedTime": { "type": "string", "format": "date-time" }
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
                  "title": { "type": "string", "description": "Task title" },
                  "content": { "type": "string", "description": "Task content/description" },
                  "projectId": { "type": "string", "description": "Project ID (optional)" },
                  "dueDate": { "type": "string", "format": "date-time", "description": "Due date in ISO 8601 format (e.g. 2023-10-01T12:00:00+0000)" },
                  "priority": { "type": "integer", "description": "0: None, 1: Low, 3: Medium, 5: High" }
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
4. Priority levels are: 0 (None), 1 (Low), 3 (Medium), 5 (High). Map user terms like "urgent" to High (5) and "important" to Medium (3) or High depending on context.
5. Dates should be formatted as ISO 8601 strings if possible, or clear text that the API understands if supported. For this API, use ISO 8601 (e.g., "2023-12-31T23:59:59+0000").

If you encounter a 401/403 error, it means authentication failed or is missing.
"""

def get_ticktick_tools(access_token: str) -> List[Any]:
    """
    Generate TickTick tools using OpenAPIToolset.
    """
    toolset = OpenAPIToolset(
        spec_str=TICKTICK_OPENAPI_SPEC,
        spec_str_type='json',
        # Inject the Authorization header for all requests
        headers={"Authorization": f"Bearer {access_token}"}
    )
    return [toolset]

async def create_ticktick_agent(user_id: str) -> Optional[Agent]:
    """
    Create a configured TickTick Agent for the specific user.
    Retrieves the user's TickTick token from the database.
    """
    # 1. Get the credential
    cred = await _get_credential(user_id, CredentialType.TICKTICK_TOKEN)
    
    if not cred or not cred.get('token'):
        # If no token, we can't create a functional agent with these tools
        # The calling system should handle this (e.g., prompt for auth)
        return None

    access_token = cred['token']

    # 2. Generate tools
    tools = get_ticktick_tools(access_token)

    # 3. Create Agent
    agent = Agent(
        model='gemini-2.0-flash-exp',  # Or configured model
        name='ticktick_manager',
        description='Specialized agent for managing TickTick tasks and projects.',
        instruction=TICKTICK_AGENT_INSTRUCTION,
        tools=tools
    )
    
    return agent

import uuid
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.adk.tools import ToolContext

async def ticktick_tool_wrapper(
    instruction: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Manage TickTick tasks and projects via a specialized AI agent.
    
    Args:
        instruction: Natural language instruction for the agent (e.g., "List my tasks", "Add a task to buy milk").
        
    Returns:
        The agent's response/result.
    """
    user_id = tool_context.state.get('user_id')
    if not user_id:
        return {"status": "error", "message": "User not identified"}

    agent = await create_ticktick_agent(user_id)
    if not agent:
        return {
            "status": "error", 
            "message": "TickTick authentication not found. Please authenticate first using the auth link."
        }

    # Create a temporary session for this interaction
    # In a real app, you might want to persist sub-agent sessions
    session_id = f"ticktick_session_{user_id}_{uuid.uuid4()}"
    session_service = InMemorySessionService()
    
    runner = Runner(
        agent=agent,
        app_name="ticktick_sub_agent",
        session_service=session_service
    )
    
    await session_service.create_session(
        app_name="ticktick_sub_agent",
        user_id=user_id,
        session_id=session_id
    )

    response_text = ""
    try:
        content = types.Content(role='user', parts=[types.Part(text=instruction)])
        
        async for event in runner.run_async(
            user_id=user_id, 
            session_id=session_id, 
            new_message=content
        ):
            if event.is_final_response() and event.content and event.content.parts:
                response_text = event.content.parts[0].text
                
        return {
            "status": "success",
            "agent_response": response_text
        }
    except Exception as e:
        return {"status": "error", "message": f"Agent execution failed: {str(e)}"}
