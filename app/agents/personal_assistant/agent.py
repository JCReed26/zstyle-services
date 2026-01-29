from langchain_community.agent_toolkits import GmailToolkit
from langchain_community.tools.gmail.utils import get_gmail_credentials, build_resource_service
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
import os

# Get the directory of the current file
current_dir = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(current_dir, "credentials.json")
TOKEN_FILE = os.path.join(current_dir, "token.json")

# Use plural 'client_secrets_file' as required by langchain-community
gmail_credentials = get_gmail_credentials(
    token_file=TOKEN_FILE,
    client_secrets_file=CREDENTIALS_FILE,
)

# GmailToolkit expects a Resource object, not Credentials
api_resource = build_resource_service(credentials=gmail_credentials)
gmail_toolkit = GmailToolkit(api_resource=api_resource)

tools = [*gmail_toolkit.get_tools()]
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)

system_prompt = "You are a helpful assistant that managed a clients inbox"

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=system_prompt
)
