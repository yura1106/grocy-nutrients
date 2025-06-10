#!/bin/bash

# Exit on any error
set -e

echo "Building Docker images..."

# Build frontend image
echo "Building frontend image..."
docker build -f docker/Dockerfile.frontend -t yuriykuznetsov/grocystat:frontend .

# Build backend image
echo "Building backend image..."
docker build -f docker/Dockerfile.backend -t yuriykuznetsov/grocystat:backend .

# Push images to Docker Hub
echo "Pushing images to Docker Hub..."
docker push yuriykuznetsov/grocystat:frontend
docker push yuriykuznetsov/grocystat:backend

echo "Done! Images have been built and pushed successfully." 