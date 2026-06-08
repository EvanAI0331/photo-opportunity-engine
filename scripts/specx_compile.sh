#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SPECX_PLUGIN_DIR="${SPECX_PLUGIN_DIR:-/Users/xin/Desktop/specx-codex-plugin}"
SPECX_CLI="$SPECX_PLUGIN_DIR/scripts/specx_cli.py"
CONTRACT_PATH="${1:-$ROOT_DIR/specx/contracts/photo_opportunity_agent.contract.json}"
OUT_DIR="$ROOT_DIR/specx/compiled"
BASENAME="$(basename "$CONTRACT_PATH" .contract.json)"

if [[ ! -f "$SPECX_CLI" ]]; then
  echo "SpecX CLI not found: $SPECX_CLI" >&2
  exit 2
fi

mkdir -p "$OUT_DIR"

python3 "$SPECX_CLI" verify "$CONTRACT_PATH" > "$OUT_DIR/$BASENAME.verify.json"
python3 "$SPECX_CLI" compile "$CONTRACT_PATH" > "$OUT_DIR/$BASENAME.compiled.json"
python3 "$SPECX_CLI" explain "$CONTRACT_PATH" > "$OUT_DIR/$BASENAME.explain.json"

echo "SpecX verified: $OUT_DIR/$BASENAME.verify.json"
echo "SpecX compiled: $OUT_DIR/$BASENAME.compiled.json"
echo "SpecX explained: $OUT_DIR/$BASENAME.explain.json"
