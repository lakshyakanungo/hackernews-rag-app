#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "--- Starting Hacker News Data Pipeline ---"

# The GitHub Action workflow already activated the virtual environment
# and set the environment variables. We just need to run the scripts.

# Navigate to the directory where the python scripts are located
cd "$(dirname "$0")/scripts"

echo "Step 1: Fetching new story data..."
python 01_fetch_hn_data.py

echo "Step 2: Embedding and upserting new stories..."
python 02_embed_and_upsert.py

echo "--- Pipeline finished successfully ---"
