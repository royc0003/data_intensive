#!/bin/bash

# Load environment variables
set -a
source .env
set +a

# Check if logged in to Docker Hub
echo "Checking Docker Hub login status..."
if ! docker info | grep -q "Username"; then
    echo "Not logged in to Docker Hub. Please login first:"
    docker login
fi

# Build and tag the image
echo "Building image..."
docker build -t ${DOCKER_USERNAME}/bookstore-api:latest .

echo "Pushing image to Docker Hub..."
docker push ${DOCKER_USERNAME}/bookstore-api:latest

echo "Done! Image pushed to: ${DOCKER_USERNAME}/bookstore-api:latest" 