variable "project_id" {
  description = "GCP project ID"
  type = string
}

variable "region" {
  description = "GCP deployment region"
  type = string
  default = "us-central1"
}

variable "lb_domain" {
    description = "Domain served by the LB (used with Cloudflare Origin Cert)"
    type = string
}

variable "cloudflare_ip_ranges" {
    description = "Cloudflare edge IP ranges allowed through Cloud Armor. See: https://www.cloudflare.com/ips/"
    type = list(string)
}

variable "cr_proxy_service_name" {
    default = "agent-connect-server"
}

variable "cr_proxy_image" {
    description = "Container image for the proxy service"
    type = string
}

variable "cr_agent_service_name" {
    description = "Name of the agent Cloud Run service (has own infra setup)"
    type = string
}

variable "min_instances" {
    default = 0
}

variable "max_instances" {
    default = 1
}

variable "ssl_cert_secret_id" {
    description = "The ID of the secret in Secret Manager containing the SSL certificate PEM."
    type        = string
}

variable "ssl_key_secret_id" {
    description = "The ID of the secret in Secret Manager containing the SSL private key PEM."
    type        = string
}
