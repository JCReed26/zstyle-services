provider "google" {
    project = var.project_id
    region = var.region
}

provider "google_beta" {
    project = var.project_id
    region = var.region
}