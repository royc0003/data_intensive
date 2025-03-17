#!/bin/bash

# Load environment variables
set -a
source .env
set +a

# Build and push using docker-compose
echo "Building image..."
docker-compose build

echo "Pushing image to Docker Hub..."
docker push ${DOCKER_USERNAME}/bookstore-api:latest

echo "Done! Image pushed to: ${DOCKER_USERNAME}/bookstore-api:latest" 