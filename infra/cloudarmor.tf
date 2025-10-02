resource "google_compute_security_policy" "cf_allowlist" {
    name = "cf-allowlist"
    description = "Only allow Cloudflare IPs"

    rule {
      action = "allow"
      priority = 1000
      match {
        versioned_expr = "SRC_IPS_V1"
        config {
          src_ip_ranges = var.cloudflare_ip_ranges
        }
      }
    }

    rule {
      action = "allow"
      priority = 1010
      match {
        versioned_expr = "SRC_IPS_V1"
        config {
          src_ip_ranges = var.cloudflare_ip_ranges_two
        }
      }
    }

    rule {
      action = "deny(403)"
      priority = 2147483647
      match {
        versioned_expr = "SRC_IPS_V1"
        config {
          src_ip_ranges = ["*"]
        }
      }
    }
}