#!/bin/bash

# Load environment variables
set -a
source .env
set +a
DOCKER_USERNAME=royc003

# Check if logged in to Docker Hub
echo "Checking Docker Hub login status..."
if ! docker info | grep -q "Username"; then
    echo "Not logged in to Docker Hub. Please login first:"
    docker login
fi

# Build and tag the image
echo "Building image..."
docker build -t ${DOCKER_USERNAME}/bookstore-api:latest .
docker build -f Dockerfile.web-bff -t ${DOCKER_USERNAME}/bookstore-api:1 .
docker build -f Dockerfile.mobile-bff -t ${DOCKER_USERNAME}/bookstore-api:2 .
docker build -f Dockerfile.customer-service -t ${DOCKER_USERNAME}/bookstore-api:3 .
docker build -f Dockerfile.book-service -t ${DOCKER_USERNAME}/bookstore-api:4 .

echo "Pushing image to Docker Hub..."
docker push ${DOCKER_USERNAME}/bookstore-api:latest
docker push ${DOCKER_USERNAME}/bookstore-api:1
docker push ${DOCKER_USERNAME}/bookstore-api:2
docker push ${DOCKER_USERNAME}/bookstore-api:3
docker push ${DOCKER_USERNAME}/bookstore-api:4

echo "Done! Image pushed to: ${DOCKER_USERNAME}/bookstore-api:latest" 