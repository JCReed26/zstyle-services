# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

import google.auth
import vertexai
from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

_, project_id = google.auth.default()
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

vertexai.init(project=project_id, location="us-central1")

# Agent Tools 
from google_agents.gcal_toolset import calendar_agent
from google_agents.gmail_toolset import gmail_agent
from google_agents.gtasks_toolset import gtasks_agent


root_agent = Agent(
    name="root_agent",
    model="gemini-live-2.5-flash-preview-native-audio-09-2025",
    instruction="You are a helpful AI assistant designed to provide accurate and useful information.",
    tools=[AgentTool(calendar_agent), AgentTool(gmail_agent), AgentTool(gtasks_agent)],
)
