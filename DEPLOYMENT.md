# ZStyle Services - Production Deployment Guide

This guide walks you through deploying ZStyle Services to Google Cloud Platform (GCP) using Terraform and Cloud Run.

## Prerequisites

1. **GCP Account Setup**
   - Create a GCP project
   - Enable billing
   - Install [gcloud CLI](https://cloud.google.com/sdk/docs/install)
   - Authenticate: `gcloud auth login`
   - Set project: `gcloud config set project YOUR_PROJECT_ID`

2. **Terraform Setup**
   - Install [Terraform](https://www.terraform.io/downloads) >= 1.0
   - Verify: `terraform version`

3. **OAuth Provider Setup**
   - Google OAuth: Create credentials in [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
   - TickTick OAuth: Create app in [TickTick Developer Portal](https://developer.ticktick.com/)
   - **Note**: Redirect URIs will be configured after first deployment

4. **Secrets Preparation**
   - Collect all required secrets (see list below)
   - Have them ready to input into Secret Manager

## Required Secrets

You'll need to create these secrets in Secret Manager:

- `GOOGLE_CLIENT_ID` - Google OAuth Client ID
- `GOOGLE_CLIENT_SECRET` - Google OAuth Client Secret
- `GOOGLE_API_KEY` - Google Gemini API Key
- `TICKTICK_CLIENT_ID` - TickTick OAuth Client ID
- `TICKTICK_CLIENT_SECRET` - TickTick OAuth Client Secret
- `TELEGRAM_BOT_TOKEN` - Telegram Bot Token
- `OPENAI_API_KEY` - OpenAI API Key (for OpenMemory embeddings)
- `ENCRYPTION_KEY` - Fernet encryption key (base64-encoded, 32 bytes)
- `DATABASE_URL` - Will be generated automatically
- `DATABASE_PASSWORD` - Will be generated automatically

## Deployment Steps

### Step 1: Configure Terraform Variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your project_id and preferences
```

Edit `terraform.tfvars`:
```hcl
project_id = "your-gcp-project-id"
region     = "us-central1"
app_name   = "zstyle-services"
```

### Step 2: Initialize Terraform

```bash
terraform init
```

This downloads the required providers and sets up the backend.

### Step 3: Review Terraform Plan

```bash
terraform plan
```

Review the planned changes. You should see:
- Cloud SQL instance
- Secret Manager secrets (structure only)
- Cloud Run services
- Service accounts and IAM roles
- VPC resources (if using private IP)

### Step 4: Apply Terraform Infrastructure

```bash
terraform apply
```

Type `yes` when prompted. This will create:
- Cloud SQL PostgreSQL instance
- Secret Manager secrets (empty - you'll populate them)
- Cloud Run services (will fail initially - need secrets and image)
- Service accounts with proper permissions

**Note**: The Cloud Run services will be created but won't work until you:
1. Populate secrets
2. Build and push Docker image
3. Update Cloud Run with the image

### Step 5: Generate Encryption Key

```bash
python3 -c "from cryptography.fernet import Fernet; import base64; print(base64.urlsafe_b64encode(Fernet.generate_key()).decode())"
```

Save this output - you'll need it for the `ENCRYPTION_KEY` secret.

### Step 6: Populate Secrets

For each secret, create it in Secret Manager:

```bash
# Google OAuth
echo -n "your-google-client-id" | gcloud secrets create GOOGLE_CLIENT_ID --data-file=-
echo -n "your-google-client-secret" | gcloud secrets create GOOGLE_CLIENT_SECRET --data-file=-

# Google API Key
echo -n "your-google-api-key" | gcloud secrets create GOOGLE_API_KEY --data-file=-

# TickTick OAuth
echo -n "your-ticktick-client-id" | gcloud secrets create TICKTICK_CLIENT_ID --data-file=-
echo -n "your-ticktick-client-secret" | gcloud secrets create TICKTICK_CLIENT_SECRET --data-file=-

# Telegram Bot Token
echo -n "your-telegram-bot-token" | gcloud secrets create TELEGRAM_BOT_TOKEN --data-file=-

# OpenAI API Key
echo -n "your-openai-api-key" | gcloud secrets create OPENAI_API_KEY --data-file=-

# Encryption Key (from Step 5)
echo -n "your-encryption-key-base64" | gcloud secrets create ENCRYPTION_KEY --data-file=-
```

### Step 7: Get Database Connection Details

Get the database connection name and password:

```bash
# Connection name
terraform output database_connection_name

# Database password (from Secret Manager)
gcloud secrets versions access latest --secret="DATABASE_PASSWORD"
```

### Step 8: Create DATABASE_URL Secret

Construct the DATABASE_URL using the connection details:

```bash
# For public IP (default):
DB_PASSWORD=$(gcloud secrets versions access latest --secret="DATABASE_PASSWORD")
CONNECTION_NAME=$(terraform output -raw database_connection_name)
DB_USER=$(terraform output -raw database_user)  # or check terraform.tfvars
DB_NAME=$(terraform output -raw database_name)  # or check terraform.tfvars

# Format: postgresql+asyncpg://user:password@/dbname?host=/cloudsql/PROJECT:REGION:INSTANCE
DATABASE_URL="postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@/${DB_NAME}?host=/cloudsql/${CONNECTION_NAME}"

# Store in Secret Manager
echo -n "$DATABASE_URL" | gcloud secrets create DATABASE_URL --data-file=-
```

### Step 9: Build and Push Docker Image

```bash
# From project root (not terraform directory)
cd ..

# Build and push
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/zstyle-services:latest
```

Or use Cloud Build:

```bash
gcloud builds submit --config cloudbuild.yaml
```

### Step 10: Update Cloud Run Services

The services should automatically use the latest image, but verify:

```bash
# Get service URLs
terraform output cloud_run_url
terraform output telegram_bot_url

# Update main service
gcloud run services update zstyle-services \
  --image gcr.io/YOUR_PROJECT_ID/zstyle-services:latest \
  --region us-central1

# Update Telegram bot service
gcloud run services update zstyle-services-telegram-bot \
  --image gcr.io/YOUR_PROJECT_ID/zstyle-services:latest \
  --region us-central1
```

### Step 11: Update OAuth Redirect URIs

Get your Cloud Run URL:

```bash
terraform output google_redirect_uri
terraform output ticktick_redirect_uri
```

**Google OAuth Console**:
1. Go to [Google Cloud Console > APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials)
2. Edit your OAuth 2.0 Client ID
3. Add Authorized redirect URI: `https://YOUR_SERVICE_URL/api/oauth/google/callback`
4. Save

**TickTick Developer Portal**:
1. Go to your TickTick app settings
2. Update OAuth redirect URL: `https://YOUR_SERVICE_URL/api/oauth/ticktick/callback`
3. Save

**Update Secret Manager** (optional - if using CLOUD_RUN_URL env var):
```bash
CLOUD_RUN_URL=$(terraform output -raw cloud_run_url)
gcloud secrets versions add GOOGLE_REDIRECT_URI --data-file=- <<< "${CLOUD_RUN_URL}/api/oauth/google/callback"
gcloud secrets versions add TICKTICK_REDIRECT_URI --data-file=- <<< "${CLOUD_RUN_URL}/api/oauth/ticktick/callback"
```

### Step 12: Run Database Migrations

The application will automatically create tables on startup, but you can verify:

```bash
# Connect to Cloud SQL
gcloud sql connect INSTANCE_NAME --user=zstyle_user

# In PostgreSQL:
\c zstyle
\dt  # List tables
```

Or use a Cloud Run job:

```bash
gcloud run jobs create migrate-db \
  --image gcr.io/YOUR_PROJECT_ID/zstyle-services:latest \
  --region us-central1 \
  --command python \
  --args reset_db.py \
  --set-env-vars USE_POSTGRES=true \
  --set-secrets DATABASE_URL=DATABASE_URL:latest
```

### Step 13: Verify Deployment

1. **Health Check**:
   ```bash
   curl $(terraform output -raw cloud_run_url)/health
   ```

2. **Test OAuth Flow**:
   - Visit: `https://YOUR_SERVICE_URL/api/oauth/google/authorize?user_id=test-user`
   - Complete OAuth flow
   - Verify callback works

3. **Test Telegram Bot**:
   - Send a message to your Telegram bot
   - Verify it responds

4. **Check Logs**:
   ```bash
   gcloud logging read "resource.type=cloud_run_revision" --limit 50
   ```

## Post-Deployment

### Monitoring Setup

1. **Cloud Monitoring Alerts**:
   - Set up alerts for Cloud Run errors
   - Monitor database connections
   - Track OAuth failures

2. **Cloud Logging**:
   - Review logs regularly
   - Set up log-based metrics
   - Create dashboards

### Security Hardening

1. **Restrict IAM Access**:
   - Review service account permissions
   - Remove unnecessary roles
   - Use least privilege principle

2. **Network Security**:
   - Enable private IP for Cloud SQL (set `use_private_ip = true`)
   - Restrict Cloud Run ingress
   - Use VPC connector for private access

3. **Secret Rotation**:
   - Rotate secrets regularly
   - Use Secret Manager versioning
   - Monitor secret access

### Performance Optimization

1. **Cloud Run Scaling**:
   - Adjust `min_instances` for always-on
   - Set `max_instances` based on load
   - Monitor concurrency settings

2. **Database Optimization**:
   - Upgrade Cloud SQL tier for production
   - Enable query insights
   - Set up connection pooling

3. **Caching**:
   - Consider Redis for session storage
   - Cache OAuth tokens appropriately
   - Use CDN for static assets

## Troubleshooting

### Cloud Run Service Won't Start

1. Check logs: `gcloud logging read "resource.type=cloud_run_revision" --limit 100`
2. Verify secrets are populated
3. Check DATABASE_URL format
4. Verify service account permissions

### Database Connection Issues

1. Verify Cloud SQL instance is running
2. Check connection name format
3. Verify VPC connector (if using private IP)
4. Check service account has `cloudsql.client` role

### OAuth Callbacks Failing

1. Verify redirect URI matches exactly
2. Check OAuth provider console settings
3. Review callback endpoint logs
4. Verify state parameter handling

### Telegram Bot Not Responding

1. Check Telegram bot service logs
2. Verify TELEGRAM_BOT_TOKEN secret
3. Verify AGENT_URL points to main service
4. Check webhook configuration (if using)

## CI/CD Setup

### Cloud Build Trigger

Create a trigger for automatic deployments:

```bash
gcloud builds triggers create github \
  --repo-name=zstyle-services \
  --repo-owner=YOUR_GITHUB_USERNAME \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml \
  --substitutions=_SERVICE_NAME=zstyle-services,_REGION=us-central1
```

### Manual Deployment

```bash
# Build and deploy
gcloud builds submit --config cloudbuild.yaml
```

## Rollback

If deployment fails:

1. **Rollback Cloud Run**:
   ```bash
   gcloud run services update-traffic zstyle-services \
     --to-revisions PREVIOUS_REVISION=100 \
     --region us-central1
   ```

2. **Revert Terraform**:
   ```bash
   terraform destroy  # Only if necessary
   ```

## Cost Optimization

1. **Cloud SQL**:
   - Use smallest tier for development
   - Schedule automatic backups
   - Monitor storage usage

2. **Cloud Run**:
   - Set `min_instances = 0` for dev
   - Use appropriate CPU/memory
   - Monitor request counts

3. **Secrets**:
   - Secret Manager is pay-per-use
   - Minimize secret versions
   - Clean up old versions

## Support

For issues or questions:
- Check Cloud Logging
- Review Terraform state
- Consult GCP documentation
- Review application logs

## Next Steps

1. Set up custom domain (optional)
2. Configure SSL certificates
3. Set up monitoring dashboards
4. Implement backup strategy
5. Plan for scaling

