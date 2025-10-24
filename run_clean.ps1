# Windows script to clean docker and rerun

Write-Host "starting docker compose take down and rebuild"
docker-compose down --remove-orphans
docker-compose build --no-cache 

echo "starting docker compose container"
docker-compose up