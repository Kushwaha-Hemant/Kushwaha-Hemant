#!/usr/bin/env bash
# Sets the GitHub profile fields that live outside the README.
#
# These need the "user" OAuth scope, which the default gh login does not grant:
#   gh auth refresh -h github.com -s user
#
# Then run this script. It is idempotent — safe to re-run.
set -euo pipefail

BIO="Building retrieval-augmented systems and the backends around them — RAG, FastAPI, Spring Boot, pgvector. MCA student in Pune."

gh api -X PATCH user \
  -f name="Hemant Kushwaha" \
  -f bio="$BIO" \
  -f blog="https://devverse-ai.kushwaha-hemant.workers.dev" \
  -f location="Pune, India" \
  -F hireable=true \
  --jq '{name, bio, blog, location, hireable}'
