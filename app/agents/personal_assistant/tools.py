import os
from langchain_community.agent_toolkits import GmailToolkit
from langchain_community.tools.gmail.utils import get_gmail_credentials, build_resource_service

current_dir = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(current_dir, "credentials.json")
TOKEN_FILE = os.path.join(current_dir, "token.json")


def get_tools():
    """Load Gmail tools. Returns empty list if credentials not available."""
    try:
        gmail_credentials = get_gmail_credentials(
            token_file=TOKEN_FILE,
            client_secrets_file=CREDENTIALS_FILE,
        )
        api_resource = build_resource_service(credentials=gmail_credentials)
        gmail_toolkit = GmailToolkit(api_resource=api_resource)
        return [*gmail_toolkit.get_tools()]
    except Exception:
        return []


tools = get_tools()
