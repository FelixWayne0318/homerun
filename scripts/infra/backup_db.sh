#!/usr/bin/env bash
# Nightly logical backup of the homerun database.
#
# Custom-format dumps (-Fc) support selective restore via pg_restore and are
# verified with pg_restore --list before the previous backup is pruned, so a
# truncated dump never silently replaces a good one.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PG_BIN="$ROOT/data/Postgres.app/Contents/Versions/16/bin"
OUT_DIR="$ROOT/data/backups"
KEEP_BACKUPS="${HOMERUN_DB_BACKUP_KEEP:-7}"
DB_URL="${HOMERUN_DB_URL:-postgresql://homerun:homerun@127.0.0.1:5432/homerun}"

mkdir -p "$OUT_DIR"
stamp="$(date +%Y%m%d-%H%M%S)"
target="$OUT_DIR/homerun-$stamp.dump"

"$PG_BIN/pg_dump" "$DB_URL" -Fc -Z6 -f "$target.tmp"
"$PG_BIN/pg_restore" --list "$target.tmp" > /dev/null
mv "$target.tmp" "$target"

ls -1t "$OUT_DIR"/homerun-*.dump 2>/dev/null | tail -n +$((KEEP_BACKUPS + 1)) | while IFS= read -r old; do
    rm -f "$old"
done

echo "backup written: $target ($(du -h "$target" | cut -f1))"
