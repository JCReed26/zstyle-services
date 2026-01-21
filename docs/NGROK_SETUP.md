# Ngrok Setup for OAuth Mini Apps Development

## Quick Start

1. Install ngrok: `brew install ngrok/ngrok/ngrok`
2. Configure authtoken: `ngrok config add-authtoken YOUR_TOKEN`
3. Start ngrok: `make ngrok-start`
4. **RESTART APPLICATION**: `docker-compose restart app`
5. Update BotFather: `/setdomain YOUR-NGROK-DOMAIN`
6. Update OAuth providers with new redirect URIs

## Important Notes

- **Application restart is REQUIRED** after ngrok URL changes
- Free ngrok URLs change on restart - update all configs each time
- Paid ngrok plan allows reserved domains (recommended for active development)

## Troubleshooting

- If OAuth fails: Check that OAUTH_BASE_URL matches ngrok URL exactly
- If webapp doesn't open: Verify BotFather domain is set correctly
- If callback fails: Verify redirect URI matches exactly in OAuth provider console
