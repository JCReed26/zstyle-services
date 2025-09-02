resource "google_compute_security_policy" "cf_allowlist" {
    name = "cf-allowlist"
    description = "Only allow Cloudflare IPs"

    rule {
      action = "ALLOW"
      priority = 1000
      match {
        versioned_expr = "SRC_IPS_V1"
        config {
          src_ip_ranges = var.cloudflare_ip_ranges
        }
      }
    }

    rule {
      action = "DENY"
      priority = 2147483646
      match {
        versioned_expr = "SRC_IPS_V1"
        config {
          src_ip_ranges = ["*"]
        }
      }
    }
}