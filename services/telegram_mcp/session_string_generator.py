#!/usr/bin/env python3
"""
Telegram Session String Generator

This script generates a session string that can be used for Telegram authentication
with the Telegram MCP server. The session string allows for portable authentication
without storing session files.

Usage:
    python session_string_generator.py

Requirements:
    - telethon
    - python-dotenv

Note on ID Formats:
When using the MCP server, please be aware that all `chat_id` and `user_id`
parameters support integer IDs, string representations of IDs (e.g., "123456"),
and usernames (e.g., "@mychannel").
"""

#!/usr/bin/env python3
"""
Telegram Session String Generator (Async Version)

This script generates a session string that can be used for Telegram authentication
with the Telegram MCP server. The session string allows for portable authentication
without storing session files.

Usage:
    python session_string_generator.py

Requirements:
    - telethon
    - python-dotenv
"""

import os
import sys
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")

if not API_ID or not API_HASH:
    print("Error: TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in .env file")
    print("Create an .env file with your credentials from https://my.telegram.org/apps")
    sys.exit(1)

# Convert API_ID to integer
try:
    API_ID = int(API_ID)
except ValueError:
    print("Error: TELEGRAM_API_ID must be an integer")
    sys.exit(1)

print("\n----- Telegram Session String Generator -----\n")
print("This script will generate a session string for your Telegram account.")
print("You will be asked to enter your phone number and the verification code sent to your Telegram app.")
print("The generated session string can be added to your .env file.")
print("\nYour credentials will NOT be stored on any server and are only used for local authentication.\n")

async def main():
    try:
        # Create the client and start the authentication flow
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        
        # This will prompt for phone/code/password internally via stdout/stdin
        await client.start()
        
        # Save the session string
        session_string = StringSession.save(client.session)
        
        print("\nAuthentication successful!")
        print("\n----- Your Session String -----")
        print(f"\n{session_string}\n")
        print("Add this to your .env file as:")
        print(f"TELEGRAM_SESSION_STRING={session_string}")
        print("\nIMPORTANT: Keep this string private and never share it with anyone!")

        # Optional: auto-update the .env file
        # We use a simple input here (blocking is fine at this stage as we are done with async work)
        choice = input("\nWould you like to automatically update your .env file with this session string? (y/N): ")
        
        if choice.lower() == "y":
            try:
                # Read the current .env file
                if os.path.exists(".env"):
                    with open(".env", "r") as file:
                        env_contents = file.readlines()
                else:
                    env_contents = []

                # Update or add the SESSION_STRING line
                session_string_line_found = False
                for i, line in enumerate(env_contents):
                    if line.startswith("TELEGRAM_SESSION_STRING="):
                        env_contents[i] = f"TELEGRAM_SESSION_STRING={session_string}\n"
                        session_string_line_found = True
                        break

                if not session_string_line_found:
                    if env_contents and not env_contents[-1].endswith('\n'):
                        env_contents.append('\n')
                    env_contents.append(f"TELEGRAM_SESSION_STRING={session_string}\n")

                # Write back to the .env file
                with open(".env", "w") as file:
                    file.writelines(env_contents)

                print("\n.env file updated successfully!")
            except Exception as e:
                print(f"\nError updating .env file: {e}")
                print("Please manually add the session string to your .env file.")
        
        # Disconnect gracefully
        await client.disconnect()

    except Exception as e:
        print(f"\nError: {e}")
        print("Failed to generate session string. Please try again.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
