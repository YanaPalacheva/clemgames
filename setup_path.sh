#!/bin/bash

# Get the parent directory that contains both clemgames and clembench_v2
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

# Add clembench_v2 to PYTHONPATH
export PYTHONPATH="$PARENT_DIR/clembench_v2:$PYTHONPATH"

# Optional: Print the updated PYTHONPATH for debugging
echo "PYTHONPATH set to: $PYTHONPATH"
