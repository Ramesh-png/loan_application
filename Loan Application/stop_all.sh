#!/usr/bin/env bash
# Stop every service launched by run_all.sh.
set -u
cd "$(dirname "$0")"

if [ ! -d logs ]; then
  echo "No logs/ directory — nothing to stop."
  exit 0
fi

for pidfile in logs/*.pid; do
  [ -e "$pidfile" ] || continue
  name="$(basename "$pidfile" .pid)"
  pid="$(cat "$pidfile" || true)"
  if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
    echo "[stop ] $name (pid $pid)"
    kill "$pid" 2>/dev/null || true
  fi
  rm -f "$pidfile"
done

echo "Done."
