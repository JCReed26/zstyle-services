#!/bin/bash
# scripts/start-ngrok.sh
# Starts ngrok tunnel and updates .env with the new URL
set -e

PORT=${1:-8000}
ENV_FILE=${2:-.env}
MAX_RETRIES=10
RETRY_INTERVAL=2

echo "🚀 Starting ngrok tunnel on port $PORT..."

# Check if ngrok is already running
if pgrep -x "ngrok" > /dev/null; then
    echo "⚠️  Ngrok is already running. Stopping existing instance..."
    pkill ngrok || true
    sleep 2
fi

# Start ngrok in background
ngrok http $PORT --log=stdout > /tmp/ngrok.log 2>&1 &
NGROK_PID=$!

# Wait for ngrok to start
echo "⏳ Waiting for ngrok to initialize..."
sleep 3

# Retry logic to get HTTPS URL
NGROK_URL=""
for i in $(seq 1 $MAX_RETRIES); do
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | \
        python3 -c "import sys, json; \
        data = json.load(sys.stdin); \
        tunnels = data.get('tunnels', []); \
        https_tunnel = next((t for t in tunnels if t.get('proto') == 'https'), None); \
        print(https_tunnel['public_url'] if https_tunnel else '')" 2>/dev/null || echo "")
    
    if [ -n "$NGROK_URL" ]; then
        break
    fi
    
    if [ $i -lt $MAX_RETRIES ]; then
        echo "   Retry $i/$MAX_RETRIES..."
        sleep $RETRY_INTERVAL
    fi
done

if [ -z "$NGROK_URL" ]; then
    echo "❌ Failed to get ngrok URL after $MAX_RETRIES retries."
    echo "   Check ngrok logs: tail -f /tmp/ngrok.log"
    kill $NGROK_PID 2>/dev/null || true
    exit 1
fi

echo "✅ Ngrok tunnel active: $NGROK_URL"

# Extract domain (for BotFather) - FIXED: simple extraction
NGROK_DOMAIN=$(echo "$NGROK_URL" | sed 's|https://||')

# Update .env file atomically
if [ -f "$ENV_FILE" ]; then
    # Create backup
    cp "$ENV_FILE" "${ENV_FILE}.bak"
    
    # Remove old OAUTH_BASE_URL if exists (handle both with and without quotes)
    sed -i.bak '/^OAUTH_BASE_URL=/d' "$ENV_FILE" 2>/dev/null || \
    sed -i '' '/^OAUTH_BASE_URL=/d' "$ENV_FILE" 2>/dev/null || true
    
    # Add new OAUTH_BASE_URL
    echo "OAUTH_BASE_URL=$NGROK_URL" >> "$ENV_FILE"
    
    # Remove backup file
    rm -f "${ENV_FILE}.bak" "${ENV_FILE}.bak.bak" 2>/dev/null || true
    
    echo "📝 Updated $ENV_FILE with OAUTH_BASE_URL=$NGROK_URL"
else
    echo "⚠️  $ENV_FILE not found. Creating it..."
    echo "OAUTH_BASE_URL=$NGROK_URL" > "$ENV_FILE"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 CRITICAL NEXT STEPS (Required for OAuth to work):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. 🔄 RESTART YOUR APPLICATION (to load new OAUTH_BASE_URL):"
echo "   docker-compose restart app"
echo ""
echo "2. 🤖 Update BotFather domain:"
echo "   /setdomain $NGROK_DOMAIN"
echo ""
echo "3. 🔐 Update OAuth redirect URIs:"
echo "   Google: $NGROK_URL/oauth/google/callback"
echo "   TickTick: $NGROK_URL/oauth/ticktick/callback"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Press Ctrl+C to stop ngrok"
echo "Ngrok web interface: http://localhost:4040"

# Keep script running and handle cleanup
trap "echo ''; echo '🛑 Stopping ngrok...'; kill $NGROK_PID 2>/dev/null || true; exit 0" INT TERM
wait $NGROK_PID
