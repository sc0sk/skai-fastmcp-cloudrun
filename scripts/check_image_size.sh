#!/bin/bash
#
# Container Image Size Check Script
#
# Validates that the container image size increase from baseline is <50MB.
# This script should be run as part of the CI/CD pipeline after building
# the Docker image for Feature 016 (langchain-postgres upgrade).
#
# Usage:
#   ./scripts/check_image_size.sh <baseline_tag> <new_tag>
#
# Example:
#   ./scripts/check_image_size.sh skai-fastmcp-cloudrun:baseline skai-fastmcp-cloudrun:016
#
# Exit codes:
#   0: Image size increase is acceptable (<50MB)
#   1: Image size increase exceeds threshold (>=50MB)
#   2: Usage error or images not found

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Threshold in MB
THRESHOLD_MB=50

# Usage function
usage() {
    echo "Usage: $0 <baseline_tag> <new_tag>"
    echo
    echo "Example:"
    echo "  $0 skai-fastmcp-cloudrun:baseline skai-fastmcp-cloudrun:016"
    echo
    echo "Environment variables:"
    echo "  THRESHOLD_MB: Maximum acceptable size increase in MB (default: 50)"
    exit 2
}

# Check arguments
if [ $# -ne 2 ]; then
    usage
fi

BASELINE_TAG="$1"
NEW_TAG="$2"

echo "========================================"
echo "Container Image Size Check"
echo "========================================"
echo "Baseline image: $BASELINE_TAG"
echo "New image: $NEW_TAG"
echo "Threshold: ${THRESHOLD_MB}MB"
echo "========================================"
echo

# Function to get image size in bytes
get_image_size() {
    local tag="$1"
    
    # Check if image exists
    if ! docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^${tag}$"; then
        echo -e "${RED}ERROR: Image not found: ${tag}${NC}" >&2
        echo "Available images:" >&2
        docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" >&2
        exit 2
    fi
    
    # Get size in bytes
    # Docker reports size in human-readable format (e.g., "1.2GB", "500MB")
    # We need to convert to bytes for accurate comparison
    local size_human=$(docker images --format "{{.Size}}" "$tag")
    
    # Convert human-readable size to bytes
    # This function handles KB, MB, GB suffixes
    local size_bytes
    if [[ $size_human =~ ^([0-9.]+)([kKmMgG][bB])$ ]]; then
        local value="${BASH_REMATCH[1]}"
        local unit="${BASH_REMATCH[2]}"
        
        case "${unit^^}" in
            KB)
                size_bytes=$(echo "$value * 1024" | bc | cut -d. -f1)
                ;;
            MB)
                size_bytes=$(echo "$value * 1024 * 1024" | bc | cut -d. -f1)
                ;;
            GB)
                size_bytes=$(echo "$value * 1024 * 1024 * 1024" | bc | cut -d. -f1)
                ;;
            *)
                echo -e "${RED}ERROR: Unknown size unit: ${unit}${NC}" >&2
                exit 2
                ;;
        esac
    else
        echo -e "${RED}ERROR: Could not parse size: ${size_human}${NC}" >&2
        exit 2
    fi
    
    echo "$size_bytes"
}

# Function to format bytes as human-readable
format_bytes() {
    local bytes="$1"
    
    if [ "$bytes" -lt 1024 ]; then
        echo "${bytes}B"
    elif [ "$bytes" -lt $((1024 * 1024)) ]; then
        echo "$(echo "scale=2; $bytes / 1024" | bc)KB"
    elif [ "$bytes" -lt $((1024 * 1024 * 1024)) ]; then
        echo "$(echo "scale=2; $bytes / 1024 / 1024" | bc)MB"
    else
        echo "$(echo "scale=2; $bytes / 1024 / 1024 / 1024" | bc)GB"
    fi
}

# Get image sizes
echo "Retrieving image sizes..."
BASELINE_SIZE=$(get_image_size "$BASELINE_TAG")
NEW_SIZE=$(get_image_size "$NEW_TAG")

# Calculate difference
DIFF_BYTES=$((NEW_SIZE - BASELINE_SIZE))
DIFF_MB=$(echo "scale=2; $DIFF_BYTES / 1024 / 1024" | bc)

# Format sizes for display
BASELINE_SIZE_HUMAN=$(format_bytes "$BASELINE_SIZE")
NEW_SIZE_HUMAN=$(format_bytes "$NEW_SIZE")
DIFF_HUMAN=$(format_bytes "$DIFF_BYTES")

# Display results
echo
echo "----------------------------------------"
echo "Results:"
echo "----------------------------------------"
echo "Baseline size: $BASELINE_SIZE_HUMAN ($BASELINE_SIZE bytes)"
echo "New size: $NEW_SIZE_HUMAN ($NEW_SIZE bytes)"
echo
if [ "$DIFF_BYTES" -ge 0 ]; then
    echo "Size increase: $DIFF_HUMAN (${DIFF_MB}MB)"
else
    echo "Size decrease: $DIFF_HUMAN (${DIFF_MB}MB)"
fi
echo "----------------------------------------"
echo

# Check against threshold
THRESHOLD_BYTES=$((THRESHOLD_MB * 1024 * 1024))

if [ "$DIFF_BYTES" -lt 0 ]; then
    # Size decreased - always acceptable
    echo -e "${GREEN}✅ PASS: Image size decreased (always acceptable)${NC}"
    echo
    echo "Summary:"
    echo "  - Image size decreased by $(format_bytes ${DIFF_BYTES#-})"
    echo "  - This is an improvement over baseline"
    exit 0
elif [ "$DIFF_BYTES" -le "$THRESHOLD_BYTES" ]; then
    # Size increase within threshold
    echo -e "${GREEN}✅ PASS: Image size increase is within threshold${NC}"
    echo
    echo "Summary:"
    echo "  - Image size increased by $DIFF_HUMAN (${DIFF_MB}MB)"
    echo "  - Threshold: ${THRESHOLD_MB}MB"
    echo "  - Percentage of threshold: $(echo "scale=1; $DIFF_MB * 100 / $THRESHOLD_MB" | bc)%"
    exit 0
else
    # Size increase exceeds threshold
    echo -e "${RED}❌ FAIL: Image size increase exceeds threshold${NC}"
    echo
    echo "Summary:"
    echo "  - Image size increased by $DIFF_HUMAN (${DIFF_MB}MB)"
    echo "  - Threshold: ${THRESHOLD_MB}MB"
    echo "  - Exceeds threshold by: $(echo "scale=2; $DIFF_MB - $THRESHOLD_MB" | bc)MB"
    echo
    echo "Actions:"
    echo "  1. Review Dockerfile for unnecessary dependencies"
    echo "  2. Check if all dependencies are required"
    echo "  3. Consider multi-stage builds to reduce final image size"
    echo "  4. Use 'docker history <image>' to identify large layers"
    echo "  5. If size increase is justified, update threshold"
    exit 1
fi
