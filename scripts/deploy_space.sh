#!/usr/bin/env bash
#
# Build the Expo web bundle and push it, the Flask server and the Space
# entrypoint to a Hugging Face Space.
#
# Usage:  scripts/deploy_space.sh <hf-user>/<space-name>
# e.g.    scripts/deploy_space.sh KL946/food_chart
#
# Create the Space first at https://huggingface.co/new-space with
# SDK "Gradio" and hardware "ZeroGPU". This script clones that repo and keeps
# its README.md, because HF writes the correct `sdk_version` into it.

set -euo pipefail

SPACE_ID="${1:-}"
if [[ -z "$SPACE_ID" ]]; then
  echo "usage: $0 <hf-user>/<space-name>" >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT

echo "==> Building the Expo web bundle"
cd "$REPO_ROOT/food_app"
[[ -d node_modules ]] || npm ci
rm -rf web-dist
# /api matches where app.py mounts the Flask app.
EXPO_PUBLIC_API_URL=/api \
EXPO_PUBLIC_MODEL_OPTIONS=deberta \
  npx expo export --platform web --output-dir web-dist

echo "==> Cloning the Space"
cd "$STAGING"
git clone "https://huggingface.co/spaces/$SPACE_ID" space
cd space

echo "==> Staging files"
cp "$REPO_ROOT/deploy/space/app.py" app.py
cp "$REPO_ROOT/deploy/space/requirements.txt" requirements.txt
cp "$REPO_ROOT/food_server/server.py" server.py
rm -rf web
cp -R "$REPO_ROOT/food_app/web-dist" web

if [[ ! -f README.md ]]; then
  echo "!! README.md missing from the Space repo." >&2
  echo "!! It carries the sdk/sdk_version front matter — create the Space" >&2
  echo "!! through the web UI rather than pushing to an empty repo." >&2
  exit 1
fi

echo "==> Pushing"
git add -A
if git diff --cached --quiet; then
  echo "Nothing changed."
  exit 0
fi
git commit -m "Deploy: web bundle, Flask API and Gradio demo"
git push

echo
echo "Done. Watch the build at https://huggingface.co/spaces/$SPACE_ID"
echo "App:    https://$(echo "$SPACE_ID" | tr '/_' '--' | tr '[:upper:]' '[:lower:]').hf.space"
