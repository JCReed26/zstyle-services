"""Strava MCP Server — exposes Strava data as MCP tools"""

import json
import os
import time

from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse
from mcp.server.fastmcp import FastMCP
from stravalib.client import Client

TOKEN_PATH = os.environ.get("STRAVA_TOKEN_PATH", "strava_token.json")
CLIENT_ID = os.environ.get("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.environ.get("STRAVA_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("STRAVA_REDIRECT_URI", "http://localhost:8124/strava/callback")

mcp = FastMCP("strava")


def _load_token() -> dict | None:
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH) as f:
            return json.load(f)
    return None


def _save_token(token_data: dict):
    os.makedirs(os.path.dirname(os.path.abspath(TOKEN_PATH)), exist_ok=True)
    with open(TOKEN_PATH, "w") as f:
        json.dump(token_data, f)


def get_strava_client() -> Client:
    client = Client()
    token = _load_token()
    if not token:
        return client

    # Auto-refresh if token expires within 60 seconds
    if token.get("expires_at", 0) < time.time() + 60:
        refreshed = client.refresh_access_token(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            refresh_token=token["refresh_token"],
        )
        token = {
            "access_token": refreshed["access_token"],
            "refresh_token": refreshed["refresh_token"],
            "expires_at": refreshed["expires_at"],
            "token_type": refreshed.get("token_type", "Bearer"),
        }
        _save_token(token)

    client.access_token = token["access_token"]
    client.refresh_token = token["refresh_token"]
    client.token_expires_at = token["expires_at"]
    return client


@mcp.tool()
def get_recent_activities(limit: int = 10) -> list[dict]:
    """Fetch the user's most recent Strava activities."""
    client = get_strava_client()
    if not client.access_token:
        return [{"error": "Strava not connected. Visit /strava/authorize to connect."}]
    activities = client.get_activities(limit=limit)
    return [
        {
            "name": a.name,
            "type": str(a.type),
            "distance_km": round(float(a.distance) / 1000, 2) if a.distance else 0,
            "moving_time_min": round(a.moving_time.total_seconds() / 60) if a.moving_time else 0,
            "date": str(a.start_date_local),
            "average_heartrate": a.average_heartrate,
        }
        for a in activities
    ]


@mcp.tool()
def get_athlete_stats() -> dict:
    """Fetch the authenticated athlete's all-time and recent stats."""
    client = get_strava_client()
    if not client.access_token:
        return {"error": "Strava not connected. Visit /strava/authorize to connect."}
    athlete = client.get_athlete()
    stats = client.get_athlete_stats(athlete.id)
    return {
        "recent_run_distance_km": round(float(stats.recent_run_totals.distance) / 1000, 2),
        "recent_ride_distance_km": round(float(stats.recent_ride_totals.distance) / 1000, 2),
        "ytd_run_distance_km": round(float(stats.ytd_run_totals.distance) / 1000, 2),
        "all_time_run_distance_km": round(float(stats.all_run_totals.distance) / 1000, 2),
    }


@mcp.tool()
def get_strava_auth_url() -> str:
    """Get the OAuth authorization URL for Strava. Use this to connect the user's Strava account."""
    client = Client()
    return client.authorization_url(
        client_id=CLIENT_ID,
        redirect_uri=REDIRECT_URI,
        scope=["activity:read_all", "profile:read_all"],
    )


# FastAPI app — handles OAuth flow + mounts MCP SSE
app = FastAPI(title="Strava MCP")


@app.get("/strava/authorize")
async def strava_authorize():
    """Redirect browser to Strava OAuth consent page to begin the authorization flow."""
    client = Client()
    url = client.authorization_url(
        client_id=CLIENT_ID,
        redirect_uri=REDIRECT_URI,
        scope=["activity:read_all", "profile:read_all"],
        approval_prompt="auto",
    )
    return RedirectResponse(url=url)


@app.get("/strava/callback")
async def strava_callback(code: str, state: str = None):
    """OAuth callback — exchanges auth code for token and saves strava_token.json."""
    client = Client()
    token_response = client.exchange_code_for_token(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        code=code,
    )
    token_data = {
        "access_token": token_response["access_token"],
        "refresh_token": token_response["refresh_token"],
        "expires_at": token_response["expires_at"],
        "token_type": token_response.get("token_type", "Bearer"),
    }
    _save_token(token_data)
    return JSONResponse({"status": "ok", "message": "Strava connected. Token saved."})


@app.get("/strava/status")
async def strava_status():
    """Check if Strava is connected and show token expiry."""
    token = _load_token()
    if not token:
        return JSONResponse({"connected": False, "message": "Visit /strava/authorize to connect."})
    expires_in = int(token.get("expires_at", 0) - time.time())
    return JSONResponse({
        "connected": True,
        "expires_in_seconds": expires_in,
        "token_type": token.get("token_type"),
    })


# Mount FastMCP SSE app at /sse
app.mount("/sse", mcp.sse_app())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8124)
