terraform {
  backend "gcs" {
    bucket = "totemic-phoenix-468400-j5-terraform-state"
    prefix = "zstyle/dev"
  }
}
