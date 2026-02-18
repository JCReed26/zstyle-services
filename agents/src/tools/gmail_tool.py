"""Gmail tools via langchain-google-community GmailToolkit"""

import os


GMAIL_SCOPES = ["https://mail.google.com/"]


def get_gmail_tools():
    """
    Returns Gmail tools. Requires credentials.json in agents/ directory.
    First run opens browser for OAuth consent -> saves gmail_token.json.
    Returns [] if credentials are missing (graceful degradation).
    """
    try:
        from langchain_google_community import GmailToolkit
        from langchain_google_community.gmail.utils import get_gmail_credentials, build_resource_service

        token_path = os.environ.get("GMAIL_TOKEN_PATH", "gmail_token.json")
        secrets_path = os.environ.get("GOOGLE_CLIENT_SECRETS_PATH", "credentials.json")

        credentials = get_gmail_credentials(
            token_file=token_path,
            client_secrets_file=secrets_path,
            scopes=GMAIL_SCOPES,
        )
        service = build_resource_service(credentials=credentials)
        toolkit = GmailToolkit(api_resource=service)
        return toolkit.get_tools()
    except Exception as e:
        print(f"Warning: Gmail tools unavailable: {e}")
        return []
