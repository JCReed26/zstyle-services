# Service Account for Cloud Run
resource "google_service_account" "cloud_run" {
  account_id   = "${var.app_name}-sa"
  display_name = "Cloud Run Service Account for ${var.app_name}"
}

# Grant Secret Manager access
resource "google_secret_manager_secret_iam_member" "secrets_access" {
  for_each = toset([
    google_secret_manager_secret.google_client_id.secret_id,
    google_secret_manager_secret.google_client_secret.secret_id,
    google_secret_manager_secret.google_api_key.secret_id,
    google_secret_manager_secret.ticktick_client_id.secret_id,
    google_secret_manager_secret.ticktick_client_secret.secret_id,
    google_secret_manager_secret.telegram_bot_token.secret_id,
    google_secret_manager_secret.openai_api_key.secret_id,
    google_secret_manager_secret.db_password.secret_id,
    google_secret_manager_secret.encryption_key.secret_id,
    google_secret_manager_secret.database_url.secret_id
  ])

  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run.email}"
}

# Grant Cloud SQL access
resource "google_project_iam_member" "cloud_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

# Note: Cloud Run service URL will be available after deployment
# Use terraform output to get the URL after first apply

# Cloud Run Service - Main App
resource "google_cloud_run_v2_service" "main" {
  name     = var.app_name
  location = var.region

  template {
    service_account = google_service_account.cloud_run.email

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    containers {
      image = "gcr.io/${var.project_id}/${var.app_name}:latest"

      resources {
        limits = {
          cpu    = "${var.cpu}"
          memory = var.memory
        }
      }

      # Environment variables
      env {
        name  = "USE_POSTGRES"
        value = "true"
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }

      env {
        name  = "DATABASE_NAME"
        value = var.database_name
      }

      env {
        name  = "DATABASE_USER"
        value = var.database_user
      }

      env {
        name  = "CLOUD_SQL_CONNECTION_NAME"
        value = google_sql_database_instance.main.connection_name
      }

      # Database URL from Secret Manager
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_url.secret_id
            version = "latest"
          }
        }
      }

      # OAuth Redirect URIs (will be updated after first deployment)
      env {
        name  = "GOOGLE_REDIRECT_URI"
        value = "https://${var.app_name}-${substr(sha256(var.project_id), 0, 8)}-${var.region}.a.run.app/api/oauth/google/callback"
      }

      env {
        name  = "TICKTICK_REDIRECT_URI"
        value = "https://${var.app_name}-${substr(sha256(var.project_id), 0, 8)}-${var.region}.a.run.app/api/oauth/ticktick/callback"
      }

      env {
        name  = "CLOUD_RUN_URL"
        value = "https://${var.app_name}-${substr(sha256(var.project_id), 0, 8)}-${var.region}.a.run.app"
      }

      # Secrets from Secret Manager
      env {
        name = "GOOGLE_CLIENT_ID"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.google_client_id.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "GOOGLE_CLIENT_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.google_client_secret.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "GOOGLE_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.google_api_key.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "TICKTICK_CLIENT_ID"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.ticktick_client_id.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "TICKTICK_CLIENT_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.ticktick_client_secret.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "TELEGRAM_BOT_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.telegram_bot_token.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "OPENAI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.openai_api_key.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "ENCRYPTION_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.encryption_key.secret_id
            version = "latest"
          }
        }
      }

      # Cloud SQL connection
      dynamic "env" {
        for_each = var.use_private_ip ? [] : [1]
        content {
          name  = "CLOUD_SQL_CONNECTION_NAME"
          value = google_sql_database_instance.main.connection_name
        }
      }
    }

    # VPC Access (if using private IP)
    dynamic "vpc_access" {
      for_each = var.use_private_ip ? [1] : []
      content {
        connector = google_vpc_access_connector.connector[0].id
        egress    = "PRIVATE_RANGES_ONLY"
      }
    }
  }

  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }

  depends_on = [
    google_project_service.required_apis,
    google_sql_database_instance.main
  ]
}

# Cloud Run Service - Telegram Bot
resource "google_cloud_run_v2_service" "telegram_bot" {
  name     = "${var.app_name}-telegram-bot"
  location = var.region

  template {
    service_account = google_service_account.cloud_run.email

    scaling {
      min_instance_count = var.telegram_bot_min_instances
      max_instance_count = var.telegram_bot_max_instances
    }

    containers {
      image = "gcr.io/${var.project_id}/${var.app_name}:latest"

      # Override command for Telegram bot
      command = ["python", "-m", "channels.telegram_bot"]

      resources {
        limits = {
          cpu    = "1"
          memory = "256Mi"
        }
      }

      # Environment variables
      env {
        name  = "USE_POSTGRES"
        value = "true"
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }

      env {
        name  = "AGENT_URL"
        value = "https://${var.app_name}-${substr(sha256(var.project_id), 0, 8)}-${var.region}.a.run.app"
      }

      # Database URL from Secret Manager
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_url.secret_id
            version = "latest"
          }
        }
      }

      # Secrets from Secret Manager
      env {
        name = "TELEGRAM_BOT_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.telegram_bot_token.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }

  depends_on = [
    google_project_service.required_apis,
    google_cloud_run_v2_service.main
  ]
}

# Allow unauthenticated access to main app (or configure IAM for authenticated)
resource "google_cloud_run_service_iam_member" "public_access" {
  service  = google_cloud_run_v2_service.main.name
  location = google_cloud_run_v2_service.main.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Telegram bot doesn't need public access (uses webhooks)
# But we'll allow it for now - restrict in production
resource "google_cloud_run_service_iam_member" "telegram_bot_access" {
  service  = google_cloud_run_v2_service.telegram_bot.name
  location = google_cloud_run_v2_service.telegram_bot.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

