# Secret Manager secrets
# Note: You'll need to manually create secret versions with actual values
# gcloud secrets create SECRET_NAME --data-file=- <<< "your-value"
# Or use terraform secret versions (shown below for some secrets)

resource "google_secret_manager_secret" "google_client_id" {
  secret_id = "GOOGLE_CLIENT_ID"
  
  replication {
    automatic = true
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret" "google_client_secret" {
  secret_id = "GOOGLE_CLIENT_SECRET"
  
  replication {
    automatic = true
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret" "google_api_key" {
  secret_id = "GOOGLE_API_KEY"
  
  replication {
    automatic = true
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret" "ticktick_client_id" {
  secret_id = "TICKTICK_CLIENT_ID"
  
  replication {
    automatic = true
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret" "ticktick_client_secret" {
  secret_id = "TICKTICK_CLIENT_SECRET"
  
  replication {
    automatic = true
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret" "telegram_bot_token" {
  secret_id = "TELEGRAM_BOT_TOKEN"
  
  replication {
    automatic = true
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret" "openai_api_key" {
  secret_id = "OPENAI_API_KEY"
  
  replication {
    automatic = true
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret" "encryption_key" {
  secret_id = "ENCRYPTION_KEY"
  
  replication {
    automatic = true
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret" "database_url" {
  secret_id = "DATABASE_URL"
  
  replication {
    automatic = true
  }

  depends_on = [google_project_service.required_apis]
}

