#!/bin/bash
# One-time setup: Python packages. ffmpeg must be installed.
set -e
cd "$(dirname "$0")"
pip install -q -r requirements.txt
command -v ffmpeg >/dev/null || { echo "ffmpeg is required"; exit 1; }
echo "generator setup ok"
