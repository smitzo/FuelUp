#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$project_root"

environment_file="${ORACLE_ENV_FILE:-.env.oracle}"
if [[ ! -f "$environment_file" ]]; then
  echo "Missing $environment_file. Copy .env.oracle.example and fill it in." >&2
  exit 1
fi

if [[ "${SKIP_GIT_PULL:-false}" != "true" ]]; then
  git pull --ff-only
fi

release_sha="$(git rev-parse --short HEAD)"
export RELEASE_SHA="$release_sha"

docker compose \
  --env-file "$environment_file" \
  -f compose.oracle.yaml \
  build --pull backend

docker compose \
  --env-file "$environment_file" \
  -f compose.oracle.yaml \
  up -d --remove-orphans

docker compose \
  --env-file "$environment_file" \
  -f compose.oracle.yaml \
  ps

api_domain="$(
  sed -n 's/^API_DOMAIN=//p' "$environment_file" | tail -n 1
)"
if [[ -z "$api_domain" ]]; then
  echo "API_DOMAIN is missing from $environment_file." >&2
  exit 1
fi

for attempt in {1..30}; do
  if curl --fail --silent --show-error \
    "https://${api_domain}/api/health/ready/" >/dev/null; then
    echo "FuelUp is ready at https://${api_domain}"
    exit 0
  fi
  sleep 5
done

echo "Deployment started, but readiness did not pass within 150 seconds." >&2
docker compose \
  --env-file "$environment_file" \
  -f compose.oracle.yaml \
  logs --tail=100 backend caddy
exit 1
