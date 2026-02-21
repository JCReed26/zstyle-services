"""Background automation scheduler using APScheduler"""

import os
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger


LANGGRAPH_URL = os.environ.get("LANGGRAPH_DEPLOYMENT_URL", "http://localhost:8123")


async def run_agent_task(assistant_id: str, message: str):
    """Programmatically invoke a LangGraph agent"""
    from langgraph_sdk import get_client
    client = get_client(url=LANGGRAPH_URL)
    await client.runs.create(
        thread_id=None,
        assistant_id=assistant_id,
        input={"messages": [{"role": "user", "content": message}]},
    )


def daily_email_triage():
    """8am daily: summarize inbox and flag action items"""
    asyncio.run(run_agent_task(
        "personal_assistant",
        "Run daily email triage: fetch recent emails, create digest summary, flag action items. Update the emails state."
    ))


def weekly_calendar_plan():
    """Sunday 6pm: time-block the coming week"""
    asyncio.run(run_agent_task(
        "personal_assistant",
        "Run weekly calendar planning: review user goals, create time-blocks for the coming week optimized toward their lifestyle goals. Update calendar state."
    ))


def weekly_fitness_review():
    """Sunday 8pm: pull Strava stats and adjust workout plan"""
    asyncio.run(run_agent_task(
        "health_agent",
        "Run weekly fitness review: fetch latest Strava activity data, analyze performance trends, adjust next week's workout plan toward user goals. Update fitness state."
    ))


def start_scheduler():
    scheduler = BackgroundScheduler()

    scheduler.add_job(
        daily_email_triage,
        CronTrigger(hour=8, minute=0),
        id="daily_email_triage",
        replace_existing=True,
    )
    scheduler.add_job(
        weekly_calendar_plan,
        CronTrigger(day_of_week="sun", hour=18, minute=0),
        id="weekly_calendar_plan",
        replace_existing=True,
    )
    scheduler.add_job(
        weekly_fitness_review,
        CronTrigger(day_of_week="sun", hour=20, minute=0),
        id="weekly_fitness_review",
        replace_existing=True,
    )

    scheduler.start()
    print("Automation scheduler started: 3 V1 automations active")
    return scheduler
