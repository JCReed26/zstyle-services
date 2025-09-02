terraform {
    required_version = ">= 1.5.0"

    required_providers {
        google = {
            source  = "hashicorp/google"
            version = ">= 5.30.0"
        }
        google_beta = {
            source  = "hashicorp/google-beta"
            version = ">= 5.30.0"
        }
    }
}