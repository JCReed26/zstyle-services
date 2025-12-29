# Note: DATABASE_URL secret must be created manually after Terraform apply
# because it requires the database password which is stored in Secret Manager.
# 
# Use this command after terraform apply:
# 
# DB_PASSWORD=$(gcloud secrets versions access latest --secret="DATABASE_PASSWORD")
# CONNECTION_NAME=$(terraform output -raw database_connection_name)
# DATABASE_URL="postgresql+asyncpg://${var.database_user}:${DB_PASSWORD}@/${var.database_name}?host=/cloudsql/${CONNECTION_NAME}"
# echo -n "$DATABASE_URL" | gcloud secrets create DATABASE_URL --data-file=-
#
# Or update existing secret:
# echo -n "$DATABASE_URL" | gcloud secrets versions add DATABASE_URL --data-file=-

