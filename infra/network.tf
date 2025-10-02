resource "google_compute_network" "serverless" {
    name = "serverless-vpc"
    auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "serverless" {
    name = "serverless-subnet"
    ip_cidr_range = "10.8.0.0/28"
    region = var.region
    network = google_compute_network.serverless.id  
}

resource "google_vpc_access_connector" "serverless" {
    name = "serverless-connector"
    region = var.region
    network = google_compute_network.serverless.id
    ip_cidr_range = "10.8.0.16/28"
    max_instances = 6
    min_instances = 2
}

resource "google_compute_address" "nat_ip" {
    name = "serverless-nat-ip"
    address_type = "EXTERNAL"
    lifecycle {
      prevent_destroy = true
    }
}

resource "google_compute_router" "router" {
    name = "serverless-router"
    region = var.region
    network = google_compute_network.serverless.id
}

resource "google_compute_router_nat" "nat" {
    name = "serverless-nat"
    router = google_compute_router.router.name
    region = var.region
    nat_ip_allocate_option = "MANUAL_ONLY"
    nat_ips = [ google_compute_address.nat_ip.self_link ]
    source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}