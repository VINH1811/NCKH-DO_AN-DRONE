#!/usr/bin/env bash

set -e

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <project_dir> <run_id>"
    echo "Example: $0 dt1_follow VT01-setup-20261004"
    exit 1
fi

PROJECT_DIR="$1"
RUN_ID="$2"
ENV_DIR="${PROJECT_DIR}/env/${RUN_ID}"

if [ ! -d "$PROJECT_DIR" ]; then
    echo "Error: project directory '$PROJECT_DIR' does not exist."
    exit 1
fi

mkdir -p "$ENV_DIR"

echo "Recording Python environment..."
python -m pip freeze > "${ENV_DIR}/pip_freeze.txt"

echo "Recording NVIDIA GPU environment..."
if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi > "${ENV_DIR}/nvidia_smi.txt"
else
    echo "nvidia-smi not available" > "${ENV_DIR}/nvidia_smi.txt"
fi

echo "Recording Git commit..."
git rev-parse HEAD > "${ENV_DIR}/git_commit.txt"

echo "Recording Python version..."
python --version > "${ENV_DIR}/python_version.txt" 2>&1

echo "Environment recorded:"
echo "  ${ENV_DIR}/pip_freeze.txt"
echo "  ${ENV_DIR}/nvidia_smi.txt"
echo "  ${ENV_DIR}/git_commit.txt"
echo "  ${ENV_DIR}/python_version.txt"
