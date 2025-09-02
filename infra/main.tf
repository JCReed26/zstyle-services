# Enable Required API 'services'
resource "google_project_service" "services" {
    for_each = toset([
        "run.googleapis.com",
        "compute.googleapis.com",
        "vpcaccess.googleapis.com",
        "iam.googleapis.com",
        "cloudresourcemanager.googleapis.com",
        "secretmanager.googleapis.com"
    ])
    project = var.project_id
    service = each.key
}