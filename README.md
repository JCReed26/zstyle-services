# ZStyle Web, Agent, and Backend Services 
> Note: this project is in active development

# QuickStart

1. Setup env variables

  - Rename the `.env.example` file to `.env` and update the values with your own  

  ```bash
  cp .env.example .env
  ```

2. Start docker daemon and run command below

  ```bash
  docker-compose up --build
  ```
  or  
  - MacOS/Linux:
  ```bash
  ./run_clean.sh
  ```
  - Windows:
  ```powershell
  ./run_clean.ps1
  ```

---

# Agents
The zstyle system core. The main agent from the server on main is zstyle. currently with two agent tools for gcal and gmail due to these becoming 
custom agents

---

# Backend
Currently the scraps of a test mvp. When created it will be a go server with the gin framework for handling auth, database, webhooks, permissions, and other business logic.

---

## What is ZStyle?

ZStyle is a next-generation lifestyle management system that helps users stay organized, proactive, and connected — without being controlled by technology.

Life today runs on dozens of apps — from calendars to fitness trackers, to-do lists, communication tools, and social media. ZStyle brings everything together into one intelligent, customizable system that helps you manage your goals, habits, and lifestyle across work, health, and personal life.

ZStyle doesn’t block apps or limit phone use — instead, it works with your apps to create balance, purpose, and flow. It helps users set goals, stay accountable, and stay connected with real life while leveraging technology as a tool, not a distraction.

---

### Integrated Apps

ZStyle connects with your existing tools and platforms:

> Instagram • YouTube • TikTok • Slack • Gmail • Google Calendar • TickTick • WhatsApp • Discord • Reminders • and more.

The system integrates them all into a **unified, customizable dashboard** that brings your digital life into one simple view.

---


### Agentic System

Beyond integrations, ZStyle is powered by an **AI agent network** that acts as your orchestrated life assistant.  

Each user has a set of specialized agents — such as a **fitness coach**, **nutritionist**, or **student assistant** — that collaborate through a shared context of your goals and routines.

#### Examples

- **Fitness Coach:** Integrates with Strava, gym apps, or wearables to track progress and guide workouts.  
- **Nutritionist:** Pulls from recipes, meal trackers, and calorie apps to align meal plans with your health goals.  
- **Student Assistant:** Connects to Canvas or productivity tools to manage deadlines and study schedules.

Agents can **communicate with each other**.  
For example:

> Your Fitness Coach suggests increasing calorie intake → it notifies the Nutritionist → the Nutritionist generates meal plans to match.  
> If an agent isn’t initialized, the **Orchestrator Agent** recommends activating it or finding an alternative workflow.

--- 

### Smart Event Handling

ZStyle’s agents working together can handle real-world events dynamically.  
For instance:

- A company you invest in has critical news — ZStyle can trigger an **iOS Shortcut alarm or phone call** to alert you instantly.  
- A coworker sends a tense email — ZStyle can queue it with a **drafted response** tailored to your communication style.

Each interaction contributes to **goal tracking** and **lifestyle analytics**, helping users manage their day without cognitive overload.

---

### Managers & Workflows

ZStyle’s core automation system is built around two components:

- **Managers:** Handle complex, multi-step or reactive tasks (e.g. Google ADK or CrewAI teams).  
- **Workflows:** Manage simpler, repeatable actions using LangChain or similar frameworks (triggered by users, managers, or webhooks).

Together, they power everything from scheduling and communication to automation and task completion.

---

### Circles: Social Meets Purpose

**Circles** are community spaces for users to connect around goals, habits, or interests — similar to Reddit communities but centered on **action and real-world connection**.

Users can drop **Circle Pins** on a map (e.g. “Pickup Football @ FSU Fields”).  
Nearby users interested in the same activity get notified and can join.  
Once enough users confirm, the event goes active and updates participants in real time.
Circles stay forming or active until the host deactivates it. 
Once active, as users enter the circle or become available on their schedule possible participants are notified of the circle.

---

### Dashboards: Your Life at a Glance

ZStyle provides customizable dashboards across **mobile and desktop** to keep everything relevant in one place.

Each agent can have unique dashboards tailored to its function:

- **Fitness Agent:** Workout tracking, goal monitoring, and set-recording with form review.  
- **Student Assistant:** Class schedules, deadlines, and study planning tools.

Everything is context-aware and adjustable to your lifestyle.

---

### A2A (Agent-to-Agent)

ZStyle doesn’t stop with its own ecosystem — it connects with external AI systems.  
If you pay for AI agents in other platforms (like Notion), your ZStyle Lifestyle Agent can **delegate tasks** directly to those agents.  

As more third-party ai agent integrations become available, ZStyle will evolve into a **fully connected AI ecosystem** designed around you.

---

### The Vision

ZStyle’s mission is to **put humans back at the center of technology**.  
It’s not about using less tech — it’s about using it **intentionally** to:

- Stay organized and proactive  
- Reconnect with real life  
- Build healthy routines and communities  
- Create time for creativity, play, and rest  

ZStyle helps you look up from your phone — and **start taking control of your lifestyle with ZStyle**.

---

#### Research and Development Teams
Formation is in progress
