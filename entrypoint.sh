#!/bin/bash
# ===========================================
# Container Entrypoint Script
# ===========================================
# Handles directory permissions before starting the application
# Runs as root, creates directories, then switches to appuser

set -e

# Data directories that need to exist with correct permissions
DATA_DIRS=(
    "/app/data"
    "/app/data/results"
)

# Create directories and set ownership
for dir in "${DATA_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "Creating directory: $dir"
        mkdir -p "$dir"
    fi
    chown appuser:appuser "$dir"
done

# Switch to appuser and execute the command
exec gosu appuser "$@"
