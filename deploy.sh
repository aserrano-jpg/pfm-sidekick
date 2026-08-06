#!/bin/bash
# deploy.sh - push changes to GitHub and trigger Streamlit redeploy
# Usage: ./deploy.sh "your commit message"

MSG="${1:-Update dashboard}"
TOKEN=$(security find-generic-password -s "github-pfm-sidekick" -w 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "GitHub token not found in keychain. Run setup first:"
  echo "  security add-generic-password -s github-pfm-sidekick -a aserrano-jpg -w YOUR_TOKEN"
  exit 1
fi

cd /Users/aserrano/Downloads/pfm-sidekick
git add -A
git commit -m "$MSG"
git push https://aserrano-jpg:${TOKEN}@github.com/aserrano-jpg/pfm-sidekick.git main

echo ""
echo "Deployed. Streamlit will redeploy in ~60 seconds."
