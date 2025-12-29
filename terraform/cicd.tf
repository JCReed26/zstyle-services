# Cloud Build Service Account
resource "google_service_account" "cloud_build" {
  account_id   = "${var.app_name}-build-sa"
  display_name = "Cloud Build Service Account for ${var.app_name}"
}

# Grant Cloud Build permissions
resource "google_project_iam_member" "cloud_build_roles" {
  for_each = toset([
    "roles/run.admin",
    "roles/iam.serviceAccountUser",
    "roles/storage.admin",
    "roles/secretmanager.secretAccessor"
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.cloud_build.email}"
}

# Cloud Build Trigger (manual - configure in Cloud Console or via gcloud)
# This is a template - actual triggers should be created via Cloud Console
# or gcloud commands after initial deployment

