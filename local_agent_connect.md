# Local Agent Connect Setup Guide

This guide shows how to connect to your Cloud Run service locally for development using the secure `gcloud run services proxy` method.

## Quick Setup (Recommended)

### Prerequisites
- Google Cloud CLI installed and authenticated
- "Cloud Run Invoker" role for the target service

### 1. Verify Authentication
```bash
# Check your authentication status
gcloud auth list
gcloud config list project

# Set correct project if needed
gcloud config set project totemic-phoenix-468400-j5
```

### 2. Start the Proxy
```bash
# Replace [YOUR_SERVICE_REGION] with your service region (e.g., us-central1)
gcloud run services proxy zstyle --project totemic-phoenix-468400-j5 --port 8080 --region [YOUR_SERVICE_REGION]
```

### 3. Access Your Service
- Open browser: `http://localhost:8080`
- Use in development tools: Postman, curl, local applications
- All requests are automatically authenticated and forwarded

## Security Benefits

✅ **Authenticated Access**: Uses your gcloud identity  
✅ **Local Only**: Accessible only from your machine  
✅ **No Public Exposure**: Service remains private  

# Alternative: Temporary Public Access

⚠️ **Use with extreme caution and only when absolutely necessary**

### Enable Public Access
1. Go to Google Cloud Console → Cloud Run
2. Select your `zstyle` service
3. Click **Permissions** tab
4. Click **Grant Access**
5. Add `allUsers` with `Cloud Run Invoker` role
6. Confirm the warning

### Access Public URL
- Find URL on service overview page
- Format: `https://zstyle-[HASH]-[REGION].run.app`

### 🚨 CRITICAL: Revert Immediately After Use
1. Return to **Permissions** tab
2. Remove `allUsers` entry (trash icon)
3. Click **Save**

### Why Revert?
- **Security Risk**: Exposes service to potential exploits
- **Cost Risk**: Unexpected traffic charges

## Troubleshooting

**Port in use?** Change `--port 8080` to another port (e.g., `--port 8000`)

**Permission denied?** Ensure your account has "Cloud Run Invoker" role

**Wrong project?** Verify with `gcloud config list project`

---

**Recommendation**: Always use the proxy method for local development. It's secure, easy, and handles authentication automatically.
