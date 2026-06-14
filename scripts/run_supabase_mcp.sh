#!/usr/bin/env bash
# Cursor MCP entrypoint: loads backend/.env and starts @supabase/mcp-server-supabase.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/backend/.env"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ENV_FILE"
  set +a
fi

if [[ -z "${SUPABASE_ACCESS_TOKEN:-}" ]]; then
  echo "SUPABASE_ACCESS_TOKEN missing. Add it to backend/.env (Supabase dashboard → Account → Access Tokens)." >&2
  exit 1
fi

PROJECT_REF="${SUPABASE_PROJECT_REF:-}"
if [[ -z "$PROJECT_REF" && -n "${SUPABASE_URL:-}" ]]; then
  PROJECT_REF="$(printf '%s' "$SUPABASE_URL" | sed -n 's|https://\([^.]*\)\.supabase\.co.*|\1|p')"
fi

if [[ -z "$PROJECT_REF" ]]; then
  echo "Set SUPABASE_URL or SUPABASE_PROJECT_REF in backend/.env." >&2
  exit 1
fi

exec npx -y @supabase/mcp-server-supabase@latest \
  --project-ref "$PROJECT_REF" \
  --features database
