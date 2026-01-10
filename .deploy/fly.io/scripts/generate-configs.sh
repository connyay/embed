#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${ROOT_DIR:-$(dirname "$SCRIPT_DIR")}"

CONFIG_FILE="$ROOT_DIR/config.yaml"
TEMPLATE_FILE="$ROOT_DIR/templates/fly.toml.tmpl"
APPS_DIR="$ROOT_DIR/apps"

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "Error: config.yaml not found at $CONFIG_FILE"
    exit 1
fi

if [[ ! -f "$TEMPLATE_FILE" ]]; then
    echo "Error: template not found at $TEMPLATE_FILE"
    exit 1
fi

if ! command -v yq &> /dev/null; then
    echo "Error: yq is required. Install with: brew install yq"
    exit 1
fi

# Clean and recreate apps directory
rm -rf "$APPS_DIR"
mkdir -p "$APPS_DIR"

# Read defaults
DEFAULT_IMAGE=$(yq '.defaults.image // "ghcr.io/huggingface/text-embeddings-inference:cpu-1.8"' "$CONFIG_FILE")
DEFAULT_PRIMARY_REGION=$(yq '.defaults.primary_region // "ord"' "$CONFIG_FILE")
DEFAULT_VM_SIZE=$(yq '.defaults.vm_size // "shared-cpu-2x"' "$CONFIG_FILE")
DEFAULT_MEMORY=$(yq '.defaults.memory // 2048' "$CONFIG_FILE")
DEFAULT_MIN_MACHINES=$(yq '.defaults.min_machines // 1' "$CONFIG_FILE")
DEFAULT_MAX_MACHINES=$(yq '.defaults.max_machines // 2' "$CONFIG_FILE")
DEFAULT_AUTO_STOP=$(yq '.defaults.auto_stop // "suspend"' "$CONFIG_FILE")
DEFAULT_AUTO_START=$(yq '.defaults.auto_start // true' "$CONFIG_FILE")
DEFAULT_INTERNAL_PORT=$(yq '.defaults.internal_port // 80' "$CONFIG_FILE")
DEFAULT_VOLUME_SIZE=$(yq '.defaults.volume_size // 10' "$CONFIG_FILE")
DEFAULT_EXTRA_ARGS=$(yq '.defaults.extra_args // ""' "$CONFIG_FILE")

# Get list of app names
APP_NAMES=$(yq '.apps | keys | .[]' "$CONFIG_FILE")

for APP_NAME in $APP_NAMES; do
    # Read app-specific config with defaults
    IMAGE=$(yq ".apps.\"$APP_NAME\".image // \"$DEFAULT_IMAGE\"" "$CONFIG_FILE")
    MODEL_ID=$(yq ".apps.\"$APP_NAME\".model_id // \"\"" "$CONFIG_FILE")
    PRIMARY_REGION=$(yq ".apps.\"$APP_NAME\".primary_region // \"$DEFAULT_PRIMARY_REGION\"" "$CONFIG_FILE")
    VM_SIZE=$(yq ".apps.\"$APP_NAME\".vm_size // \"$DEFAULT_VM_SIZE\"" "$CONFIG_FILE")
    MEMORY=$(yq ".apps.\"$APP_NAME\".memory // $DEFAULT_MEMORY" "$CONFIG_FILE")
    MIN_MACHINES=$(yq ".apps.\"$APP_NAME\".min_machines // $DEFAULT_MIN_MACHINES" "$CONFIG_FILE")
    MAX_MACHINES=$(yq ".apps.\"$APP_NAME\".max_machines // $DEFAULT_MAX_MACHINES" "$CONFIG_FILE")
    AUTO_STOP=$(yq ".apps.\"$APP_NAME\".auto_stop // \"$DEFAULT_AUTO_STOP\"" "$CONFIG_FILE")
    AUTO_START=$(yq ".apps.\"$APP_NAME\".auto_start // $DEFAULT_AUTO_START" "$CONFIG_FILE")
    INTERNAL_PORT=$(yq ".apps.\"$APP_NAME\".internal_port // $DEFAULT_INTERNAL_PORT" "$CONFIG_FILE")
    VOLUME_SIZE=$(yq ".apps.\"$APP_NAME\".volume_size // $DEFAULT_VOLUME_SIZE" "$CONFIG_FILE")
    EXTRA_ARGS=$(yq ".apps.\"$APP_NAME\".extra_args // \"$DEFAULT_EXTRA_ARGS\"" "$CONFIG_FILE")

    # Generate volume name from app name (replace dashes with underscores)
    VOLUME_NAME="${APP_NAME//-/_}_data"

    # Validate model_id is set
    if [[ -z "$MODEL_ID" || "$MODEL_ID" == "null" ]]; then
        echo "Error: model_id is required for app '$APP_NAME'"
        exit 1
    fi

    # Create app directory
    APP_DIR="$APPS_DIR/$APP_NAME"
    mkdir -p "$APP_DIR"

    # Generate fly.toml from template
    sed -e "s|{{APP_NAME}}|$APP_NAME|g" \
        -e "s|{{IMAGE}}|$IMAGE|g" \
        -e "s|{{MODEL_ID}}|$MODEL_ID|g" \
        -e "s|{{PRIMARY_REGION}}|$PRIMARY_REGION|g" \
        -e "s|{{VM_SIZE}}|$VM_SIZE|g" \
        -e "s|{{MEMORY}}|$MEMORY|g" \
        -e "s|{{MIN_MACHINES}}|$MIN_MACHINES|g" \
        -e "s|{{MAX_MACHINES}}|$MAX_MACHINES|g" \
        -e "s|{{AUTO_STOP}}|$AUTO_STOP|g" \
        -e "s|{{AUTO_START}}|$AUTO_START|g" \
        -e "s|{{INTERNAL_PORT}}|$INTERNAL_PORT|g" \
        -e "s|{{VOLUME_NAME}}|$VOLUME_NAME|g" \
        -e "s|{{VOLUME_SIZE}}|$VOLUME_SIZE|g" \
        -e "s|{{EXTRA_ARGS}}|$EXTRA_ARGS|g" \
        "$TEMPLATE_FILE" > "$APP_DIR/fly.toml"

    echo "Generated: $APP_DIR/fly.toml"
done

echo ""
echo "Generated $(echo "$APP_NAMES" | wc -l | tr -d ' ') app configurations in $APPS_DIR"
echo ""
echo "Done! Run 'make list' to see all apps."
