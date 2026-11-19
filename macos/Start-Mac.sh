#!/bin/bash
set -euo pipefail
APP="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
ROOT="$(dirname -- "$APP")"
if [ "$(uname -s)" != Darwin ]; then echo 'Este acceso requiere macOS.'; exit 1; fi
for LABEL in com.segmentiq.ollama com.segmentiq.local; do
  if ! launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1; then
    launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/$LABEL.plist"
  fi
  launchctl kickstart "gui/$(id -u)/$LABEL"
done
"$ROOT/runtime/python/bin/python" -c 'import json,time,urllib.request
for attempt in range(60):
 try:
  result=json.load(urllib.request.urlopen("http://127.0.0.1:8765/health",timeout=2))
  assert result.get("service")=="SEGMENT IQ"
  break
 except (OSError,ValueError,AssertionError):time.sleep(1)
else:raise SystemExit("No se ha podido iniciar SEGMENT IQ. Revisa los registros locales.")'
if [ "${1:-}" = --browser ]; then open 'http://127.0.0.1:8765'; fi
