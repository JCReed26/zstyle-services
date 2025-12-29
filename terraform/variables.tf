variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "zstyle-services"
}

variable "database_tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-f1-micro"  # Change for production
}

variable "database_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "zstyle"
}

variable "database_user" {
  description = "PostgreSQL database user"
  type        = string
  default     = "zstyle_user"
}

variable "min_instances" {
  description = "Minimum Cloud Run instances"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum Cloud Run instances"
  type        = number
  default     = 10
}

variable "cpu" {
  description = "CPU allocation for Cloud Run"
  type        = number
  default     = 1
}

variable "memory" {
  description = "Memory allocation for Cloud Run (in GB or Mi)"
  type        = string
  default     = "512Mi"
}

variable "use_private_ip" {
  description = "Use private IP for Cloud SQL"
  type        = bool
  default     = false  # Set to true for production
}

variable "telegram_bot_min_instances" {
  description = "Minimum Cloud Run instances for Telegram bot"
  type        = number
  default     = 0
}

variable "telegram_bot_max_instances" {
  description = "Maximum Cloud Run instances for Telegram bot"
  type        = number
  default     = 1
}

