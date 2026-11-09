#!/usr/bin/env bash
# Copy-truncate rotation for the launchd-managed worker logs.
#
# The worker planes keep their log file descriptor open across rotations, so
# the file is copied to an archive and then truncated in place instead of
# renamed: a rename would leave the plane writing to the archived inode and
# the fresh path would never receive new lines.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LOG_DIR="$ROOT/data"
MAX_BYTES="${HOMERUN_LOG_MAX_BYTES:-52428800}"
KEEP_ARCHIVES="${HOMERUN_LOG_KEEP_ARCHIVES:-3}"

[ -d "$LOG_DIR" ] || exit 0
shopt -s nullglob

for file in "$LOG_DIR"/*.log; do
    size="$(stat -f%z "$file")"
    [ "$size" -ge "$MAX_BYTES" ] || continue

    stamp="$(date +%Y%m%d-%H%M%S)"
    cp "$file" "$file.$stamp"
    : > "$file"
    gzip -f "$file.$stamp"

    # Keep the newest N archives per log, drop the rest.
    ls -1t "$file".*.gz 2>/dev/null | tail -n +$((KEEP_ARCHIVES + 1)) | while IFS= read -r old; do
        rm -f "$old"
    done

    echo "rotated $file (was $((size / 1048576)) MB) -> $file.$stamp.gz"
done
