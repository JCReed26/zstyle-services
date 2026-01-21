#!/usr/bin/env python3
"""
Ngrok Helper Script - Cross-platform ngrok management

Starts ngrok tunnel and updates .env file with HTTPS URL
"""
import subprocess
import time
import json
import requests
import os
import sys
import signal
from pathlib import Path


def get_ngrok_url(max_retries=10, retry_interval=2):
    """Get the public HTTPS URL from ngrok API with retry logic."""
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get("http://localhost:4040/api/tunnels", timeout=2)
            if response.status_code == 200:
                data = response.json()
                tunnels = data.get("tunnels", [])
                for tunnel in tunnels:
                    if tunnel.get("proto") == "https":
                        return tunnel.get("public_url")
        except requests.RequestException:
            pass
        
        if attempt < max_retries:
            print(f"   Retry {attempt}/{max_retries}...")
            time.sleep(retry_interval)
    
    return None


def update_env_file(ngrok_url, env_file=".env"):
    """Update .env file with OAUTH_BASE_URL atomically."""
    env_path = Path(env_file)
    
    # Read existing content
    lines = []
    if env_path.exists():
        lines = env_path.read_text().split('\n')
    
    # Remove old OAUTH_BASE_URL
    lines = [line for line in lines 
             if not line.strip().startswith('OAUTH_BASE_URL=')]
    
    # Add new OAUTH_BASE_URL
    lines.append(f"OAUTH_BASE_URL={ngrok_url}")
    
    # Write atomically (write to temp, then rename)
    temp_path = env_path.with_suffix('.env.tmp')
    temp_path.write_text('\n'.join(lines))
    temp_path.replace(env_path)
    
    print(f"✅ Updated {env_file} with OAUTH_BASE_URL={ngrok_url}")


def start_ngrok(port=8000):
    """Start ngrok tunnel and return process."""
    print(f"🚀 Starting ngrok tunnel on port {port}...")
    
    # Check if ngrok already running
    try:
        response = requests.get("http://localhost:4040/api/tunnels", timeout=1)
        if response.status_code == 200:
            print("⚠️  Ngrok is already running. Stopping existing instance...")
            subprocess.run(["pkill", "ngrok"], capture_output=True)
            time.sleep(2)
    except:
        pass
    
    # Start ngrok
    process = subprocess.Popen(
        ["ngrok", "http", str(port), "--log=stdout"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for ngrok to start
    print("⏳ Waiting for ngrok to initialize...")
    time.sleep(3)
    
    return process


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    env_file = sys.argv[2] if len(sys.argv) > 2 else ".env"
    
    # Start ngrok
    process = start_ngrok(port)
    
    # Get URL
    ngrok_url = get_ngrok_url()
    
    if not ngrok_url:
        print("❌ Failed to get ngrok URL. Check if ngrok is running.")
        process.terminate()
        sys.exit(1)
    
    print(f"✅ Ngrok tunnel active: {ngrok_url}")
    
    # Update .env
    update_env_file(ngrok_url, env_file)
    
    # Extract domain
    ngrok_domain = ngrok_url.replace("https://", "")
    
    # Print instructions
    print("\n" + "="*80)
    print("📋 CRITICAL NEXT STEPS (Required for OAuth to work):")
    print("="*80)
    print(f"\n1. 🔄 RESTART YOUR APPLICATION:")
    print(f"   docker-compose restart app")
    print(f"\n2. 🤖 Update BotFather domain:")
    print(f"   /setdomain {ngrok_domain}")
    print(f"\n3. 🔐 Update OAuth redirect URIs:")
    print(f"   Google: {ngrok_url}/oauth/google/callback")
    print(f"   TickTick: {ngrok_url}/oauth/ticktick/callback")
    print("="*80)
    print("\nPress Ctrl+C to stop ngrok")
    print("Ngrok web interface: http://localhost:4040")
    
    # Handle cleanup
    def signal_handler(sig, frame):
        print("\n🛑 Stopping ngrok...")
        process.terminate()
        process.wait()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Wait for process
    try:
        process.wait()
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()
