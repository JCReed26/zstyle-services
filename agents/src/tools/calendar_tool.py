"""Google Calendar tools via langchain-google-community CalendarToolkit"""

import os


CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_tools():
    """
    Returns Calendar tools. Requires same credentials.json as Gmail.
    Saves calendar_token.json on first OAuth run.
    Returns [] if credentials are missing (graceful degradation).
    """
    try:
        from langchain_google_community import CalendarToolkit
        from langchain_google_community.calendar.utils import get_google_credentials, build_resource_service

        token_path = os.environ.get("CALENDAR_TOKEN_PATH", "calendar_token.json")
        secrets_path = os.environ.get("GOOGLE_CLIENT_SECRETS_PATH", "credentials.json")

        credentials = get_google_credentials(
            token_file=token_path,
            client_secrets_file=secrets_path,
            scopes=CALENDAR_SCOPES,
        )
        service = build_resource_service(credentials=credentials)
        toolkit = CalendarToolkit(api_resource=service)
        return toolkit.get_tools()
    except Exception as e:
        print(f"Warning: Calendar tools unavailable: {e}")
        return []