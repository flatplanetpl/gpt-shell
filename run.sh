#!/usr/bin/env bash
set -euo pipefail
if [ ! -d "venv" ]; then
  echo "Brak venv. Uruchom ./setup.sh"
  exit 1
fi
source venv/bin/activate
# Autoload .env (jeśli istnieje)
[ -f .env ] && set -a && . ./.env && set +a
: "${OPENAI_API_KEY:?Ustaw OPENAI_API_KEY w .env albo środowisku}"
export OPENAI_MODEL="${OPENAI_MODEL:-gpt-5}"
export WORKDIR="${WORKDIR:-$PWD}"
export STREAM_PARTIAL="${STREAM_PARTIAL:-1}"
export REVIEW_PASS="${REVIEW_PASS:-1}"
export CLIFS_CONTEXT="${CLIFS_CONTEXT:-$PWD/clifs.context.json}"
export MAX_BYTES_PER_READ="${MAX_BYTES_PER_READ:-60000}"
export MAX_OUTPUT_TOKENS="${MAX_OUTPUT_TOKENS:-1024}"
export MAX_HISTORY_MSGS="${MAX_HISTORY_MSGS:-24}"
python3 cli_assistant_fs.py
