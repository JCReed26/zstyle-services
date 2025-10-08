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

import datetime
import os
from zoneinfo import ZoneInfo

import google.auth
from google.adk.agents import Agent

from app.tool_agents.gcal_toolset import calendar_agent
from app.tool_agents.gmail_toolset import gmail_agent
from app.tool_agents.gtasks_toolset import gtasks_agent

_, project_id = google.auth.default()
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")


def get_current_time() -> str:
    """Gets the current time

    Returns:
        A string with the current time.
    """
    tz = ZoneInfo('America/New_York')
    now = datetime.datetime.now(tz)
    return now.strftime('%Y-%m-%d %H:%M:%S %Z%z')


root_agent = Agent(
    name="root_agent",
    model="gemini-2.0-flash-exp",
    description="A lifecoach and personal assistant",
    instruction="You are a helpful AI Life Coach and Personal assistant designed to be a friendly support through life events."
    "You have 3 sub_agents that relate to external pieces of software that interact with the users everyday life for example"
    "calendar_agent, gmail_agent, and gtasks_agent are all google workspace tools with specific ways to create entries"
    "when creating an entry ensure to get all the information you must collect first before prompting for anything else and try to fill in"
    "as many gaps as possible based upon the users input" \
    "you have 1 tools get_current_time which returns to you the current time",
    tools=[get_current_time],
    sub_agents=[
        calendar_agent,
        gmail_agent,
        gtasks_agent,
    ]
)

print(f"DEBUG: Agent initialized with model: {root_agent.model}")
