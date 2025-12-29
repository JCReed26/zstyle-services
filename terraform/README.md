# Terraform Infrastructure for ZStyle Services

This directory contains Terraform configuration for deploying ZStyle Services to Google Cloud Platform.

## Structure

- `versions.tf` - Provider configuration
- `variables.tf` - Input variables
- `main.tf` - API enablement
- `database.tf` - Cloud SQL setup
- `secrets.tf` - Secret Manager secrets
- `cloudrun.tf` - Cloud Run services
- `cicd.tf` - CI/CD configuration
- `outputs.tf` - Output values
- `terraform.tfvars.example` - Example variables file

## Quick Start

1. Copy the example variables file:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. Edit `terraform.tfvars` with your project details

3. Initialize Terraform:
   ```bash
   terraform init
   ```

4. Review the plan:
   ```bash
   terraform plan
   ```

5. Apply the configuration:
   ```bash
   terraform apply
   ```

6. After apply, populate secrets (see DEPLOYMENT.md)

7. Create DATABASE_URL secret manually (see database_url.tf comments)

## Important Notes

- Secrets are created empty - you must populate them manually
- DATABASE_URL must be created after terraform apply (requires password)
- Cloud Run services will fail until secrets are populated and image is built
- OAuth redirect URIs must be updated after first deployment

## Outputs

After applying, use `terraform output` to see:
- Cloud Run service URLs
- Database connection name
- OAuth redirect URIs
- Service account email

## Destroying

To tear down all resources:
```bash
terraform destroy
```

**Warning**: This will delete the database and all data!

