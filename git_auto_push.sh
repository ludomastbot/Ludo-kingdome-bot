#!/bin/bash

# Navigate to your bot directory
cd ~/ludo_bot

# Add all changes
git add .

# Commit with timestamp
git commit -m "Auto-update: $(date +'%Y-%m-%d %H:%M:%S')"

# Push to main branch
git push origin main
