#!/usr/bin/env bash
# Download FileGator (MIT licensed, https://filegator.io) into vendor/filegator.
#
# FileGator is a dependency, not part of this repository: install.sh runs this
# script and copies the result to /opt/netusbflash/filegator. For development
# run it once; scripts/dev-server.sh then serves the file manager under /fm/.
#
#   ./packaging/fetch-filegator.sh            # download if missing
#   ./packaging/fetch-filegator.sh --force    # download again
#
# By default the latest official build is used. Set FILEGATOR_URL to pin
# another build, e.g. a release from https://github.com/filegator/filegator/releases.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/vendor/filegator"
LATEST_URL="https://github.com/filegator/static/raw/master/builds/filegator_latest.zip"
FALLBACK_URL="https://github.com/filegator/filegator/releases/download/v7.8.3/filegator_v7.8.3.zip"
URL="${FILEGATOR_URL:-$LATEST_URL}"

if [ "${1:-}" != "--force" ] && [ -f "$DEST/vendor/autoload.php" ] && [ -d "$DEST/dist" ]; then
    echo "FileGator already present in $DEST (use --force to download again)."
    exit 0
fi

for tool in curl unzip; do
    command -v "$tool" >/dev/null || { echo "$tool is required" >&2; exit 1; }
done
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "Downloading FileGator from $URL ..."
if ! curl -fsSL -o "$TMP/filegator.zip" "$URL"; then
    if [ -z "${FILEGATOR_URL:-}" ]; then
        echo "Latest build not reachable, using $FALLBACK_URL"
        curl -fsSL -o "$TMP/filegator.zip" "$FALLBACK_URL"
    else
        exit 1
    fi
fi
unzip -q "$TMP/filegator.zip" -d "$TMP/x"
COMPOSER_JSON="$(find "$TMP/x" -maxdepth 2 -name composer.json | head -1)"
SRC="$(dirname "${COMPOSER_JSON:-/nonexistent/x}")"
[ -n "$COMPOSER_JSON" ] && [ -f "$SRC/vendor/autoload.php" ] && [ -d "$SRC/dist" ] \
    || { echo "Unexpected archive layout" >&2; exit 1; }

rm -rf "$DEST"
mkdir -p "$(dirname "$DEST")"
# Only what is needed at runtime: no sample repository, no private data, no docs.
mkdir -p "$DEST"
cp -a "$SRC/backend" "$SRC/dist" "$SRC/vendor" "$SRC/LICENSE" "$SRC/composer.json" "$DEST/"
rm -f "$DEST/dist/index.php"
VERSION="$(grep -o "APP_VERSION', '[^']*'" "$SRC/dist/index.php" | sed "s/.*', '//; s/'//" || true)"
echo "${VERSION:-unknown}" > "$DEST/VERSION"
echo "FileGator ${VERSION:-unknown} installed in $DEST"
