output "cloud_run_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_v2_service.main.uri
}

output "telegram_bot_url" {
  description = "Telegram Bot Cloud Run service URL"
  value       = google_cloud_run_v2_service.telegram_bot.uri
}

output "database_connection_name" {
  description = "Cloud SQL connection name"
  value       = google_sql_database_instance.main.connection_name
}

output "database_public_ip" {
  description = "Cloud SQL public IP (if enabled)"
  value       = var.use_private_ip ? null : google_sql_database_instance.main.public_ip_address
}

output "service_account_email" {
  description = "Cloud Run service account email"
  value       = google_service_account.cloud_run.email
}

output "google_redirect_uri" {
  description = "Google OAuth redirect URI to configure"
  value       = "https://${google_cloud_run_v2_service.main.uri}/api/oauth/google/callback"
}

output "ticktick_redirect_uri" {
  description = "TickTick OAuth redirect URI to configure"
  value       = "https://${google_cloud_run_v2_service.main.uri}/api/oauth/ticktick/callback"
}

output "database_url_secret_name" {
  description = "Secret Manager secret name for DATABASE_URL"
  value       = google_secret_manager_secret.database_url.secret_id
}

