# Database Setup

## Quick Setup

1. **Configure Environment Variables**
   - Set `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` in `.env`
   - Set `DATABASE_URL=postgresql://postgres:password@db:5432/zstyle_db`

2. **Start PostgreSQL Container**
   ```bash
   docker compose up -d db
   ```

3. **Run Migration**
   ```bash
   docker compose cp docs/migrations/001_initial_schema.sql db:/tmp/
   docker compose exec db psql -U postgres -d zstyle_db -f /tmp/001_initial_schema.sql
   ```

4. **Verify**
   - Application verifies connection on startup
   - Check logs for "Database connection verified successfully"

## Connection String Format

- **Local Container**: `postgresql://user:password@db:5432/database`
- Uses Docker service name `db` for internal DNS resolution
- No external DNS resolution required

## Schema Management

- **Never use** `Base.metadata.create_all()` - schema managed via migrations
- **Create migrations** in `docs/migrations/` directory
- **Run migrations** via `docker compose exec db psql`

## Troubleshooting

**Connection Error**: Verify container is running: `docker compose ps db`  
**Schema Not Found**: Run migration SQL file  
**Data Loss**: Check volume exists: `docker volume ls | grep postgres_data`
