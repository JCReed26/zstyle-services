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
    ingress = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCING"

    template {
      service_account = google_service_account.agent-connect-serverless
        scaling {
            min_instance_count = var.min_instances
            max_instance_count = var.max_instances
        }

        containers {
            image = var.cr_proxy_image
            env = concat(
                [for k,v in var.proxy_env : { name = k, value = v }],
                [
                    {
                        name = "AGENT_SERVICE_URL"
                        value = data.google_cloud_run_service.zstyle.status[0].url
                    }
                ]
            )
            ports { container_port = 8080 }
        }

        vpc_access {
            connector = google_vpc_access_connector.serverless.id
            egress = "ALL_TRAFFIC"
        }
    }
}

# Allow proxy to call agent 
resource "google_cloud_run_service_iam_member" "agent_invoker" {
    location = var.region
    service = data.google_cloud_run_service.zstyle.name
    role = "roles/run.invoker"
    member = "serviceAccount:${google_service_account.agent-connect-serverless.email}"
}