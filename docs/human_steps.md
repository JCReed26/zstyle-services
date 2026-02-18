# Human Steps — Manual OAuth Setup

These steps cannot be automated. Complete them before running the Ralph Loop or asking Claude to test the application.

---

## Step 1: Google Cloud — Gmail + Calendar

**Where to go:** https://console.cloud.google.com

**What to do:**

1. Create a new project (name it "zstyle" or similar)
2. Enable two APIs:
   - Search "Gmail API" → Enable
   - Search "Google Calendar API" → Enable
3. Go to **APIs & Services → OAuth consent screen**
   - User type: **External**
   - App name: ZStyle
   - Add your Google email as a test user
   - Scopes: add `https://mail.google.com/` and `https://www.googleapis.com/auth/calendar`
   - Save
4. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
   - Application type: **Desktop app**
   - Name: zstyle-local
   - Click Create
5. Click **Download JSON** on the credential you just created
6. Rename the downloaded file to `credentials.json`
7. Place it here: `agents/credentials.json`

**What to tell Claude:**
> "credentials.json is in agents/ — ready for Google OAuth"

---

## Step 2: Run Google OAuth Consent (First-Time Only)

After `credentials.json` is in place and the agent server is running:

```bash
cd agents
uv run python -c "
from src.tools.gmail_tool import get_gmail_tools
from src.tools.calendar_tool import get_calendar_tools
print('Gmail:', [t.name for t in get_gmail_tools()])
print('Calendar:', [t.name for t in get_calendar_tools()])
"
```

- A browser window will open for each — sign in with your Google account and click Allow
- This saves `gmail_token.json` and `calendar_token.json` in `agents/`
- Subsequent runs will not open a browser

**What to tell Claude:**
> "Google OAuth done — gmail_token.json and calendar_token.json are in agents/"

---

## Step 3: Strava App

**Where to go:** https://www.strava.com/settings/api

**What to do:**

1. Log in to Strava
2. Under **My API Application**, fill in:
   - Application Name: ZStyle
   - Category: Other
   - Club: (leave blank)
   - Website: `http://localhost`
   - Authorization Callback Domain: `localhost`
3. Click Update
4. Copy your **Client ID** and **Client Secret**
5. Add them to your `.env` file at the repo root:
   ```
   STRAVA_CLIENT_ID=your_client_id_here
   STRAVA_CLIENT_SECRET=your_client_secret_here
   ```

**What to tell Claude:**
> "Strava app created — STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET are in .env"

---

## Step 4: Strava OAuth Token (First-Time Only)

After the Strava MCP server is running (`docker compose up strava-mcp` or `cd mcp/strava && python server.py`):

1. Open a browser and go to: `http://localhost:8124/docs`
2. Find the `get_strava_auth_url` tool and call it — it returns an authorization URL
3. Paste that URL in your browser, log in to Strava, click Authorize
4. Strava redirects to `http://localhost:8124/strava/callback?code=...`
5. The server exchanges the code and saves `strava_token.json`

**What to tell Claude:**
> "Strava OAuth done — strava_token.json is saved"

---

## Checklist Before Asking Claude to Test

```
[ ] agents/credentials.json exists (downloaded from Google Cloud Console)
[ ] agents/gmail_token.json exists (ran Google OAuth consent)
[ ] agents/calendar_token.json exists (ran Google OAuth consent)
[ ] .env has GOOGLE_API_KEY set
[ ] .env has STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET set
[ ] strava_token.json saved (ran Strava OAuth flow)
```

Once all boxes are checked, tell Claude:
> "OAuth setup complete — all tokens in place. Ready to test."

Claude will then run `docker compose up --build` and use Playwright MCP to smoke test the application.
