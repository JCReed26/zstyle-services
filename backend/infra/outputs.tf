output "lb_ip_address" {
    value = google_compute_global_address.lb_ip.address
    description = "Point Cloudflare A record here"
}

output "proxy_url" {
    value = google_cloud_run_v2_service.agent-connect-server.uri
}

output "agent_url"{
    value = data.google_cloud_run_service.zstyle.status[0].url
}

output "static_egress_ip" {
    value = google_compute_address.nat_ip.address
    description = "Whitelist in MongoDB Atlas"
}