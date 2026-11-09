#!/bin/bash
# LaunchAgent entrypoint for Postgres.
#
# macOS sends SIGKILL to postgres on shutdown, so a stale postmaster.pid
# survives into the next boot and the server refuses to start (the recorded
# PID may even be reused by an unrelated system process).  launchd's
# KeepAlive then retries forever and the whole stack stays down.
#
# This wrapper archives the stale lock (never deletes it) and hands off to
# postgres with the exact arguments the previous plist used.
set -euo pipefail

HOMERUN_ROOT="/Users/ahs/Projects/homerun"
PGDATA="$HOMERUN_ROOT/data/postgres"
PGBIN="$HOMERUN_ROOT/data/Postgres.app/Contents/Versions/16/bin"
PIDFILE="$PGDATA/postmaster.pid"

if [ -f "$PIDFILE" ]; then
  PID="$(head -n 1 "$PIDFILE" | tr -d '[:space:]')"
  if ! ps -p "$PID" -o comm= 2>/dev/null | grep -q postgres; then
    mv "$PIDFILE" "$PIDFILE.stale.$(date +%Y%m%d%H%M%S)"
  fi
fi

exec "$PGBIN/postgres" -D "$PGDATA" -h 127.0.0.1 -p 5432
