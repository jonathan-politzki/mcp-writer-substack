#!/bin/bash

# Shell script to launch the Writer Tool MCP server
# This script is called by Claude Desktop

# Change to the directory of this script
cd "$(dirname "$0")"

# Activate the virtual environment
source .venv/bin/activate

# Run the writer tool
python writer_tool.py 