"""Strava MCP Server — exposes Strava data as MCP tools"""

import json
import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP
from stravalib.client import Client

TOKEN_PATH = os.environ.get("STRAVA_TOKEN_PATH", "strava_token.json")
CLIENT_ID = os.environ.get("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.environ.get("STRAVA_CLIENT_SECRET")

mcp = FastMCP("strava")


def get_strava_client() -> Client:
    client = Client()
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH) as f:
            token_data = json.load(f)
        client.access_token = token_data["access_token"]
        client.refresh_token = token_data.get("refresh_token")
        client.token_expires_at = token_data.get("expires_at")
    return client


@mcp.tool()
def get_recent_activities(limit: int = 10) -> list[dict]:
    """Fetch the user's most recent Strava activities."""
    client = get_strava_client()
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
    url = client.authorization_url(
        client_id=CLIENT_ID,
        redirect_uri=os.environ.get("STRAVA_REDIRECT_URI", "http://localhost:8124/strava/callback"),
        scope=["activity:read_all", "profile:read_all"],
    )
    return url


# FastAPI app — handles OAuth callback + mounts MCP SSE
app = FastAPI(title="Strava MCP")


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
    os.makedirs(os.path.dirname(os.path.abspath(TOKEN_PATH)), exist_ok=True)
    with open(TOKEN_PATH, "w") as f:
        json.dump(token_data, f)
    return JSONResponse({"status": "ok", "message": "Strava connected. Token saved."})


# Mount FastMCP SSE app at /sse
app.mount("/sse", mcp.sse_app())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8124)
