#!/bin/bash
set -euo pipefail
umask 077
SOURCE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ROOT="${SEGMENT_IQ_INSTALL_ROOT:-$HOME/Library/Application Support/SEGMENT IQ}"
if [ "$(uname -s)" != Darwin ] || [ "$(uname -m)" != arm64 ]; then
  echo 'Este instalador local es para Mac con Apple Silicon.'; exit 1
fi
MAJOR="$(sw_vers -productVersion | cut -d. -f1)"
if [ "$MAJOR" -lt 14 ]; then echo 'Se necesita macOS 14 Sonoma o posterior.'; exit 1; fi
echo 'SEGMENT IQ · instalación local para Apple Silicon'
echo 'Instalará Python, Blender, Ollama, Codex y el motor en tu usuario.'
echo 'La primera preparación descarga varios GB. No necesita el PC del laboratorio.'
mkdir -p "$ROOT/runtime/downloads" "$ROOT/runtime/uv"
UV_ARCHIVE="$ROOT/runtime/downloads/uv-0.13.9-arm64.tar.gz"
UV_SHA='5aeca67f2283f75235de40d0bd9c0a5bbc5fce23b6d48b3bf9fa1b2db08382ca'
if [ ! -f "$UV_ARCHIVE" ] || [ "$(shasum -a 256 "$UV_ARCHIVE" | cut -d' ' -f1)" != "$UV_SHA" ]; then
  curl --fail --location --retry 3 --proto '=https' --tlsv1.2 \
    'https://github.com/astral-sh/uv/releases/download/0.13.9/uv-aarch64-apple-darwin.tar.gz' -o "$UV_ARCHIVE.part"
  if [ "$(shasum -a 256 "$UV_ARCHIVE.part" | cut -d' ' -f1)" != "$UV_SHA" ]; then echo 'La descarga de uv no coincide con su firma SHA-256.'; exit 1; fi
  mv "$UV_ARCHIVE.part" "$UV_ARCHIVE"
fi
tar -xzf "$UV_ARCHIVE" -C "$ROOT/runtime/uv" --strip-components=1
UV="$ROOT/runtime/uv/uv"
export UV_PYTHON_INSTALL_DIR="$ROOT/runtime/python-managed"
"$UV" python install 3.12
PYTHON="$("$UV" python find --managed-python 3.12)"
"$PYTHON" "$SOURCE/macos/install_local.py" --source "$SOURCE" --root "$ROOT" "$@"
echo 'Instalación preparada. Los archivos y los registros están en:'
echo "$ROOT"
