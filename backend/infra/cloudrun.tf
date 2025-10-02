resource "google_service_account" "agent-connect-serverless" {
    account_id = "${var.cr_proxy_service_name}-sa"
    display_name = "agent-connect-server"
}

# Lookup existing agent service (deployed separately)
data "google_cloud_run_service" "zstyle" {
    name = var.cr_agent_service_name
    location = var.region
}

resource "google_cloud_run_v2_service" "agent-connect-server" {
    name = var.cr_proxy_service_name
    location = var.region
    ingress = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

    template {
      service_account = google_service_account.agent-connect-serverless.email
        scaling {
            min_instance_count = var.min_instances
            max_instance_count = var.max_instances
        }

        containers {
            image = var.cr_proxy_image

            env {
                name  = "AGENT_URL"
                # The python code expects a bare domain to prepend "wss://". We extract just the hostname.
                # e.g., "https://my-service-abc-uc.a.run.app" -> "my-service-abc-uc.a.run.app"
                value = trimsuffix(replace(data.google_cloud_run_service.zstyle.status[0].url, "https://", ""), "/")
            }
            env {
                name = "MONGO_DB_URI"
                value_source {
                    secret_key_ref {
                        secret  = var.mongo_db_uri_secret_id
                        version = "latest"
                    }
                }
            }

            ports { container_port = 8080 }
        }

        vpc_access {
            connector = google_vpc_access_connector.serverless.id
            egress = "ALL_TRAFFIC"
        }
    }
    client_version = "NO_AUTHENTICATION"
    deletion_protection = false
}

# Allow proxy to call agent
resource "google_cloud_run_service_iam_member" "agent_invoker" {
    location = var.region
    service = data.google_cloud_run_service.zstyle.name
    role = "roles/run.invoker"
    member = "serviceAccount:${google_service_account.agent-connect-serverless.email}"
}

# Allow service account to access MongoDB URI secret
resource "google_secret_manager_secret_iam_member" "mongo_db_uri_accessor" {
    project = var.project_id
    secret_id = var.mongo_db_uri_secret_id
    role = "roles/secretmanager.secretAccessor"
    member = "serviceAccount:${google_service_account.agent-connect-serverless.email}"
}
