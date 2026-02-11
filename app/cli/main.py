#!/usr/bin/env python3
"""Simple CLI for testing ZStyle agents."""

import asyncio
import httpx
import click
import os
from typing import Optional

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
AGENTS = [
    "exec_func_coach",
    "fitness_coach",
    "nutritionist",
    "personal_assistant",
]

async def chat_with_agent(agent_name: str, user_id: str, message: str) -> str:
    """Send a message to an agent and get response."""
    url = f"{BACKEND_URL}/api/v1/chat/{agent_name}"
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                url,
                json={"user_id": user_id, "message": message}
            )
            response.raise_for_status()
            data = response.json()
            return data["response"]
        except httpx.ConnectError as e:
            click.echo(f"\n❌ Cannot connect to backend at {BACKEND_URL}", err=True)
            click.echo(f"   Error: {e}", err=True)
            return None
        except httpx.HTTPStatusError as e:
            click.echo(f"\n❌ Backend Error {e.status_code}:", err=True)
            try:
                error_detail = e.response.json()
                click.echo(f"   {error_detail}", err=True)
            except:
                click.echo(f"   {e.response.text}", err=True)
            return None
        except Exception as e:
            click.echo(f"\n❌ Unexpected Error: {type(e).__name__}: {str(e)}", err=True)
            import traceback
            click.echo(traceback.format_exc(), err=True)
            return None


async def chat_loop(agent_name: str, user_id: str):
    """Interactive chat loop with an agent."""
    click.echo(f"\n🤖 Chatting with {agent_name} (user: {user_id})")
    click.echo("Type 'exit' or 'quit' to return to menu, 'back' for agent menu\n")

    while True:
        try:
            message = click.prompt("You").strip()
            if not message:
                continue
            if message.lower() in ("exit", "quit"):
                raise KeyboardInterrupt
            if message.lower() == "back":
                return

            response = await chat_with_agent(agent_name, user_id, message)
            if response is None:
                # Error already printed by chat_with_agent
                continue
            click.echo(f"\n{agent_name}: {response}\n")
        except (KeyboardInterrupt, EOFError):
            click.echo("\n\nGoodbye!")
            raise


def select_agent() -> Optional[str]:
    """Show agent menu and return selected agent."""
    click.echo("\n📋 Available Agents:")
    for i, agent in enumerate(AGENTS, 1):
        click.echo(f"  {i}. {agent}")
    click.echo(f"  {len(AGENTS) + 1}. Exit")

    while True:
        try:
            choice = click.prompt("Select agent", type=int)
            if 1 <= choice <= len(AGENTS):
                return AGENTS[choice - 1]
            elif choice == len(AGENTS) + 1:
                return None
            else:
                click.echo("Invalid choice, try again")
        except (ValueError, click.Abort):
            click.echo("Invalid input")


@click.command()
@click.option(
    "--user-id",
    default="dev_user",
    help="User ID for conversation tracking",
    envvar="ZSTYLE_USER_ID"
)
@click.option(
    "--agent",
    help="Start with specific agent (exec_func_coach, fitness_coach, etc.)"
)
@click.option(
    "--backend",
    default="http://localhost:8000",
    help="Backend URL",
    envvar="BACKEND_URL"
)
def main(user_id: str, agent: Optional[str], backend: str):
    """ZStyle Agent CLI - Chat with multiple AI agents."""
    global BACKEND_URL
    BACKEND_URL = backend

    click.echo("🎯 ZStyle Services - Agent CLI")
    click.echo(f"📍 Backend: {BACKEND_URL}")
    click.echo(f"👤 User: {user_id}\n")

    try:
        # If agent specified, start with that
        if agent:
            if agent not in AGENTS:
                click.echo(f"❌ Unknown agent: {agent}")
                click.echo(f"Available: {', '.join(AGENTS)}")
                return
            asyncio.run(chat_loop(agent, user_id))
        else:
            # Interactive menu loop
            while True:
                selected_agent = select_agent()
                if selected_agent is None:
                    break
                asyncio.run(chat_loop(selected_agent, user_id))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
