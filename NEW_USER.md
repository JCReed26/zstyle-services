# New User Setup Guide: Executive Function Coach

This guide will help you set up your personal AI assistant using Google ADK and Telegram. The assistant connects to Telegram via MCP (Model Context Protocol) and integrates with Google Calendar for scheduling.

## Prerequisites

1.  **Docker Desktop**: Install Docker Desktop for your OS.
2.  **Google Cloud Project**: You need a Google Cloud Project with the **Gemini API** enabled.
3.  **Telegram Account**: You need a Telegram account to create a bot.

## Step 1: Create a Telegram Bot

1.  Open Telegram and search for **@BotFather**.
2.  Send the command `/newbot`.
3.  Follow the prompts to name your bot (e.g., "MyPersonalAssistant") and give it a username (e.g., "My_AI_Assistant_Bot").
4.  **Important**: BotFather will give you a **HTTP API Token**. Copy this token. It looks like: `123456789:ABCdefGhIJKlmNoPQRstuVWxyz`.
5.  Also, get your **API ID** and **API Hash** (required for the underlying library):
    *   Go to [https://my.telegram.org/apps](https://my.telegram.org/apps).
    *   Log in with your phone number.
    *   Click "API development tools".
    *   Create a new application (values don't matter much, you can use "PersonalApp").
    *   Copy the **App api_id** and **App api_hash**.

## Step 2: Generate Telegram Session String

1.  Install required dependencies for session generation:
    ```bash
    pip install telethon python-dotenv
    ```
2.  Run the session generator:
    ```bash
    python services/telegram_mcp/session_string_generator.py
    ```
3.  Copy the generated session string to your `.env` file.

## Step 3: Configure Environment Variables

1.  Copy the example environment file:
    ```bash
    cp .env.example .env
    ```
2.  Open `.env` in a text editor and fill in the following:

    ```env
    # Gemini API Key (Get from Google AI Studio)
    GOOGLE_API_KEY=your_gemini_api_key_here

    # Telegram Configuration
    TELEGRAM_API_ID=12345678            # From my.telegram.org
    TELEGRAM_API_HASH=abcdef123456...   # From my.telegram.org
    TELEGRAM_BOT_TOKEN=123456:ABC...    # From BotFather
    TELEGRAM_SESSION_STRING=your_session_string_here

    # Database (Default is set for local SQLite, no change needed)
    DATABASE_URL=sqlite+aiosqlite:///zstyle.db
    ```

## Step 4: Run the Application

1.  Open your terminal in the project folder.
2.  Build and start the application using Docker:
    ```bash
    docker-compose up --build
    ```
3.  Wait for the logs to say `Application startup complete`.

## Step 5: Chat with Your Coach

1.  Open Telegram.
2.  Search for your bot's username (e.g., `@My_AI_Assistant_Bot`).
3.  Click **Start** or send a message like "Hello!".
4.  The message is processed by the Executive Function Coach agent, which can help with scheduling and organization via Google Calendar integration.

## Troubleshooting

*   **"Error initializing Telegram Client"**: Check your API ID, Hash, Session String, and Bot Token in `.env`.
*   **"TELEGRAM_BOT_TOKEN not found"**: Ensure `.env` is correctly loaded.
*   **Agent not responding**: Check logs for the application. Ensure it's running on port 8000.
*   **Database Errors**: If you changed database settings, run `docker-compose down -v` to reset volumes, or delete `zstyle.db` locally.
*   **Logs**: Check `mcp_errors.log` for Telegram MCP issues.
