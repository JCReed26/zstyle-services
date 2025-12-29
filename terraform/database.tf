# Random password for database
resource "random_password" "db_password" {
  length  = 16
  special = true
}

# Store database password in Secret Manager
resource "google_secret_manager_secret" "db_password" {
  secret_id = "DATABASE_PASSWORD"
  
  replication {
    automatic = true
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}

# VPC Network (if using private IP)
resource "google_compute_network" "vpc" {
  count                   = var.use_private_ip ? 1 : 0
  name                    = "${var.app_name}-vpc"
  auto_create_subnetworks = false

  depends_on = [google_project_service.required_apis]
}

resource "google_compute_subnetwork" "subnet" {
  count         = var.use_private_ip ? 1 : 0
  name          = "${var.app_name}-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.vpc[0].id
}

# VPC Connector for Cloud Run (if using private IP)
resource "google_vpc_access_connector" "connector" {
  count         = var.use_private_ip ? 1 : 0
  name          = "${var.app_name}-connector"
  region        = var.region
  network       = google_compute_network.vpc[0].name
  ip_cidr_range = "10.8.0.0/28"
  
  depends_on = [google_project_service.required_apis]
}

# Cloud SQL Instance
resource "google_sql_database_instance" "main" {
  name             = "${var.app_name}-db"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier                        = var.database_tier
    deletion_protection_enabled = false  # Set to true for production
    
    ip_configuration {
      ipv4_enabled                                  = !var.use_private_ip
      private_network                               = var.use_private_ip ? google_compute_network.vpc[0].id : null
      enable_private_path_for_google_cloud_services = var.use_private_ip
      
      # Allow Cloud Run to connect (if using public IP)
      dynamic "authorized_networks" {
        for_each = var.use_private_ip ? [] : [1]
        content {
          name  = "cloud-run"
          value = "0.0.0.0/0"  # Restrict this in production!
        }
      }
    }

    backup_configuration {
      enabled    = true
      start_time = "03:00"
    }

    insights_config {
      query_insights_enabled = true
    }
  }

  depends_on = [
    google_project_service.required_apis,
    google_compute_network.vpc
  ]
}

# Cloud SQL Database
resource "google_sql_database" "main" {
  name     = var.database_name
  instance = google_sql_database_instance.main.name
}

# Cloud SQL User
resource "google_sql_user" "main" {
  name     = var.database_user
  instance = google_sql_database_instance.main.name
  password = random_password.db_password.result
}

