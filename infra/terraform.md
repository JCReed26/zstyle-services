 # Terraform Infrastructure Overview

This document provides a high-level summary of the Google Cloud infrastructure managed by this Terraform project.

## What is Built?

This configuration creates a secure, scalable, and production-ready environment on Google Cloud to host the `agent-connect-server` application. The key components are:

*   **External HTTPS Load Balancer**: A global load balancer with a static IP address to receive all incoming traffic.
*   **Cloud Armor Security Policy**: A firewall rule attached to the load balancer that only allows traffic from Cloudflare's IP ranges, protecting the application from direct attacks.
*   **Cloud Run Service**: The `agent-connect-server` is deployed as a serverless container, configured to only accept traffic from the load balancer.
*   **VPC Network & Cloud NAT**: A dedicated Virtual Private Cloud with a NAT gateway that provides a static egress IP address for all outbound traffic from the application.

## Purpose

The primary goals of this infrastructure are:

1.  **Security**: To prevent direct internet access to the Cloud Run service, forcing all traffic through the Cloudflare proxy and a GCP Load Balancer with a strict firewall policy.
2.  **Stability**: To provide a static, predictable IP address for both incoming traffic (via the Load Balancer) and outgoing traffic (via the Cloud NAT).
3.  **Scalability**: To leverage Google's serverless Cloud Run platform, which automatically scales the application based on traffic.

## Important Things to Note

Before deploying, you must perform a few manual setup steps. This ensures that state and secrets are handled securely.

1.  **Terraform State Bucket**: You must manually create a Google Cloud Storage (GCS) bucket to store the Terraform state file. This is a one-time setup. Update the `bucket` name in `backend.tf` to match the one you created.

    ```bash
    # Example:
    gcloud storage buckets create gs://<YOUR_UNIQUE_BUCKET_NAME> --project=<YOUR_PROJECT_ID> --location=US
    gcloud storage buckets update gs://<YOUR_UNIQUE_BUCKET_NAME> --versioning
    ```

2.  **Secrets Management**: SSL certificates and keys must be stored in Google Secret Manager, not in the repository. This configuration reads them directly from Secret Manager during deployment.

    ```bash
    # Example:
    gcloud secrets create cf-origin-cert --replication-policy="automatic"
    gcloud secrets versions add cf-origin-cert --data-file="/path/to/your/cert.pem"
    ```

3.  **`terraform.tfvars` File**: You must create a `terraform.tfvars` file in this directory to specify your project-specific variables (like `project_id`, `lb_domain`, etc.). Use `terraform.tfvars.example` as a template. **This file should not be committed to Git.**

4.  **Static Egress IP**: The Cloud NAT provides a static IP for outbound connections. You must add this IP to the allowlist of any external services your application connects to (e.g., a database firewall).

## Deployment Workflow

After the initial setup is complete, you can manage the infrastructure with the standard Terraform workflow:

1.  `terraform init` - Initializes the backend and providers.
2.  `terraform plan` - Shows what changes will be made.
3.  `terraform apply` - Applies the changes to your GCP project.