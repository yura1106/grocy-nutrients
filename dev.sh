#!/bin/bash

# Exit on any error
set -e

echo "Starting development environment..."

# Build and start the containers in development mode
docker compose -f docker-compose.dev.yml up --build

# The script will keep running until you press Ctrl+C
# When Ctrl+C is pressed, docker-compose will gracefully shut down all containers 