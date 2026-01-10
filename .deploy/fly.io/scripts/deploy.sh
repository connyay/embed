#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
APPS_DIR="$ROOT_DIR/apps"

usage() {
    echo "Usage: $0 <app-name>"
    echo ""
    echo "Deploy a TEI server to Fly.io"
    echo ""
    echo "Available apps:"
    if [[ -d "$APPS_DIR" ]]; then
        for app in "$APPS_DIR"/*/; do
            if [[ -d "$app" ]]; then
                echo "  - $(basename "$app")"
            fi
        done
    else
        echo "  (none - run 'make generate' first)"
    fi
    exit 1
}

if [[ $# -lt 1 ]]; then
    usage
fi

APP_NAME="$1"
APP_DIR="$APPS_DIR/$APP_NAME"

if [[ ! -d "$APP_DIR" ]]; then
    echo "Error: App '$APP_NAME' not found."
    echo "Run 'make generate' to generate app configs, or check 'make list'."
    exit 1
fi

if [[ ! -f "$APP_DIR/fly.toml" ]]; then
    echo "Error: fly.toml not found for app '$APP_NAME'."
    echo "Run 'make generate' to regenerate configs."
    exit 1
fi

cd "$APP_DIR"

echo "Deploying $APP_NAME..."
echo ""

# Parse fly.toml for volume and region info using yq
VOLUME_NAME=$(yq -p toml -oy '.mounts[0].source' fly.toml)
VOLUME_SIZE=$(yq -p toml -oy '.mounts[0].initial_size' fly.toml)
PRIMARY_REGION=$(yq -p toml -oy '.primary_region' fly.toml)

# Validate parsed values
if [[ -z "$VOLUME_NAME" || "$VOLUME_NAME" == "null" ]]; then
    echo "Error: Could not parse volume name from fly.toml"
    exit 1
fi
if [[ -z "$VOLUME_SIZE" || "$VOLUME_SIZE" == "null" ]]; then
    echo "Error: Could not parse volume size from fly.toml"
    exit 1
fi
if [[ -z "$PRIMARY_REGION" || "$PRIMARY_REGION" == "null" ]]; then
    echo "Error: Could not parse primary_region from fly.toml"
    exit 1
fi

echo "Volume: $VOLUME_NAME ($VOLUME_SIZE) in $PRIMARY_REGION"

# Check if app exists, create if not
if ! fly apps list --json 2>/dev/null | grep -q "\"$APP_NAME\""; then
    echo "Creating Fly.io app: $APP_NAME"
    fly apps create "$APP_NAME" --org personal
fi

# Check if volume exists, create if not
EXISTING_VOLUMES=$(fly volumes list --app "$APP_NAME" --json 2>/dev/null || echo "[]")
if ! echo "$EXISTING_VOLUMES" | grep -q "\"$VOLUME_NAME\""; then
    echo "Creating volume: $VOLUME_NAME"
    fly volumes create "$VOLUME_NAME" \
        --app "$APP_NAME" \
        --region "$PRIMARY_REGION" \
        --size "$(echo "$VOLUME_SIZE" | sed 's/[gG][bB]$//')" \
        --yes
else
    echo "Volume $VOLUME_NAME already exists"
fi

# Deploy (longer timeout for first boot model download)
echo ""
echo "Deploying..."
fly deploy --strategy rolling --wait-timeout 600

echo ""
echo "Deployed $APP_NAME successfully!"
echo "URL: https://$APP_NAME.fly.dev"
