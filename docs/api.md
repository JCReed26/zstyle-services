# API Documentation

## Endpoints

### Agent Endpoints (via Google ADK)
- `GET /apps` - List available agents
- `POST /apps/{agent_name}/users/{user_id}/sessions` - Create session
- `POST /run` - Execute agent with message

### Application Endpoints
- `GET /` - Health check
- `GET /health` - Application health status
- `GET /adk/` - ADK interface

## Authentication

OAuth2 with external services (Google Calendar, etc.) is handled through the credential service.
Session-based authentication for agent interactions.

## Data Models

### User
- `id`: UUID
- `telegram_id`: Integer
- `username`: String (optional)

### Session
- `id`: UUID
- `user_id`: UUID
- `agent_name`: String
- `session_data`: JSON

### Credential
- `id`: UUID
- `user_id`: UUID
- `service_name`: String
- `credential_data`: JSON
- `encrypted_token`: String
- `expires_at`: DateTime

### Memory
- `id`: UUID
- `user_id`: UUID
- `agent_name`: String
- `memory_type`: String
- `content`: Text
- `memory_metadata`: JSON

### Artifact
- `id`: UUID
- `session_id`: UUID
- `artifact_id`: String
- `filename`: String
- `file_path`: String
- `file_size`: Integer
- `content_type`: String