resource "google_compute_region_network_endpoint_group" "cr_neg" {
    provider = google-beta
    name = "cr-neg-${var.cr_proxy_service_name}"
    region = var.region
    network_endpoint_type = "SERVERLESS"

    cloud_run {
        service = google_cloud_run_v2_service.agent-connect-server.name
    }   
}

resource "google_compute_backend_service" "backend" {
    provider = google-beta
    name = "be-${var.cr_proxy_service_name}"
    protocol = "HTTPS"
    load_balancing_scheme = "EXTERNAL"
    

    backend {
        group = google_compute_region_network_endpoint_group.cr_neg.self_link
    }

    security_policy = google_compute_security_policy.cf_allowlist.self_link
}

resource "google_compute_url_map" "urlmap" {
    name = "urlmap-${var.cr_proxy_service_name}"
    default_service = google_compute_backend_service.backend.self_link
}

data "google_secret_manager_secret_version" "ssl_cert" {
  project = var.project_id
  secret  = var.ssl_cert_secret_id
  version = "latest"
}

data "google_secret_manager_secret_version" "ssl_key" {
  project = var.project_id
  secret  = var.ssl_key_secret_id
  version = "latest"
}

resource "google_compute_ssl_certificate" "origin_cert" {
    name = "origin-cert-${data.google_secret_manager_secret_version.ssl_cert.version}"
    private_key = data.google_secret_manager_secret_version.ssl_key.secret_data
    certificate = data.google_secret_manager_secret_version.ssl_cert.secret_data
    lifecycle {
      create_before_destroy = true
    }
}

resource "google_compute_target_https_proxy" "https_proxy" {
    name = "https-proxy"
    url_map = google_compute_url_map.urlmap.self_link
    ssl_certificates = [google_compute_ssl_certificate.origin_cert.self_link]
}

resource "google_compute_global_address" "lb_ip" {
    name = "lb-ip-${var.cr_proxy_service_name}"
    lifecycle {
      prevent_destroy = true
    }
}

resource "google_compute_global_forwarding_rule" "https_fr" {
    name = "https-fr"
    load_balancing_scheme = "EXTERNAL"
    ip_protocol = "TCP"
    port_range = "443"
    target = google_compute_target_https_proxy.https_proxy.self_link
    ip_address = google_compute_global_address.lb_ip.address
}