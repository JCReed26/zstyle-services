# Quick Start Guide - Production Deployment

This is a condensed guide for deploying ZStyle Services to GCP. For detailed instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Prerequisites Checklist

- [ ] GCP project created with billing enabled
- [ ] `gcloud` CLI installed and authenticated
- [ ] Terraform >= 1.0 installed
- [ ] OAuth credentials ready (Google, TickTick)
- [ ] All API keys ready (Google API, OpenAI, Telegram Bot Token)

## 5-Minute Deployment

### 1. Configure Terraform
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your project_id
```

### 2. Deploy Infrastructure
```bash
terraform init
terraform plan  # Review changes
terraform apply # Type 'yes'
```

### 3. Generate Encryption Key
```bash
python3 -c "from cryptography.fernet import Fernet; import base64; print(base64.urlsafe_b64encode(Fernet.generate_key()).decode())"
```

### 4. Populate Secrets
```bash
# For each secret:
echo -n "your-value" | gcloud secrets create SECRET_NAME --data-file=-

# Required secrets:
# - GOOGLE_CLIENT_ID
# - GOOGLE_CLIENT_SECRET  
# - GOOGLE_API_KEY
# - TICKTICK_CLIENT_ID
# - TICKTICK_CLIENT_SECRET
# - TELEGRAM_BOT_TOKEN
# - OPENAI_API_KEY
# - ENCRYPTION_KEY (from step 3)
```

### 5. Create DATABASE_URL Secret
```bash
DB_PASSWORD=$(gcloud secrets versions access latest --secret="DATABASE_PASSWORD")
CONNECTION_NAME=$(terraform output -raw database_connection_name)
DB_USER="zstyle_user"  # or from terraform.tfvars
DB_NAME="zstyle"       # or from terraform.tfvars

DATABASE_URL="postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@/${DB_NAME}?host=/cloudsql/${CONNECTION_NAME}"
echo -n "$DATABASE_URL" | gcloud secrets create DATABASE_URL --data-file=-
```

### 6. Build and Deploy
```bash
cd ..
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/zstyle-services:latest
```

### 7. Update OAuth Redirect URIs
```bash
# Get URLs
terraform output google_redirect_uri
terraform output ticktick_redirect_uri

# Update in:
# - Google Cloud Console > APIs & Services > Credentials
# - TickTick Developer Portal
```

### 8. Verify
```bash
curl $(terraform output -raw cloud_run_url)/health
```

## Common Issues

**Cloud Run won't start**: Check logs, verify secrets are populated
**Database connection fails**: Verify DATABASE_URL format, check Cloud SQL is running
**OAuth callbacks fail**: Verify redirect URIs match exactly

## Next Steps

- Set up Cloud Build triggers for CI/CD
- Configure monitoring alerts
- Review security settings
- Plan for scaling

For detailed troubleshooting, see [DEPLOYMENT.md](DEPLOYMENT.md).

