terraform {
  backend "gcs" {
    # This bucket must be created manually before running `terraform init`.
    # Replace this with a globally unique GCS bucket name.
    # e.g., "my-company-agent-connect-tfstate"
    bucket = "your-agent-connect-server-tfstate"
    prefix = "infra/prod"
  }
}