#!/bin/bash

# Exit on any error
set -e

echo "Building Docker images..."

# Build frontend image
echo "Building frontend image..."
docker build -f docker/Dockerfile.frontend -t yuriykuznetsov/grocynutrients:frontend .

# Build backend image
echo "Building backend image..."
docker build -f docker/Dockerfile.backend -t yuriykuznetsov/grocynutrients:backend .

# Push images to Docker Hub
echo "Pushing images to Docker Hub..."
docker push yuriykuznetsov/grocynutrients:frontend
docker push yuriykuznetsov/grocynutrients:backend

echo "Done! Images have been built and pushed successfully." 