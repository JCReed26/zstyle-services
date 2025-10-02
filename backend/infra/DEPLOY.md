## Deploying Application Updates to Production

This project uses a GitOps approach where the infrastructure is managed by Terraform and the application is deployed as a Docker container. To deploy a new version of the application code, you must build a new container image and update the Cloud Run service via Terraform.

For a detailed overview of the infrastructure, see the [Terraform Infrastructure Overview](./infra/terraform.md).

### Deployment Workflow

1.  **Make Code Changes**:
    Update the application source code as needed.

2.  **Build & Push Docker Image**:
    Build a new Docker image with your changes and push it to Google Artifact Registry. It is crucial to use a unique tag for each new build, such as a version number (`v1.1.0`) or a Git commit hash.

    ```bash
    # Example using Google Artifact Registry
    # Replace <project-id>, <repo-name>, and <tag> with your values
    export IMAGE_URI="us-central1-docker.pkg.dev/<project-id>/<repo-name>/agent-connect-server:<tag>"

    docker build -t $IMAGE_URI .
    docker push $IMAGE_URI
    ```

3.  **Update Terraform Configuration**:
    In the `infra/terraform.tfvars` file, update the `cr_proxy_image` variable to point to the new Docker image URI you just pushed.

    ```hcl
    # infra/terraform.tfvars
    cr_proxy_image = "us-central1-docker.pkg.dev/<project-id>/<repo-name>/agent-connect-server:<tag>"
    ```

4.  **Apply Terraform Changes**:
    Navigate to the `infra` directory and run `terraform apply`. Terraform will detect the change to the image URI and create a new revision of the Cloud Run service, rolling out your update with zero downtime.

    ```bash
    cd infra/
    terraform plan  # Review the planned changes
    terraform apply # Apply the update
    ```
