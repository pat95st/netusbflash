#!/usr/bin/env bash
# Download Bootstrap and Bootstrap Icons into web/public/assets/vendor.
#
# The web UI loads these files from the Pi itself (no CDN), so it also works
# without internet access. The files are committed to the repository; run this
# script only to update them (change the versions below first).
#
#   ./packaging/fetch-vendor.sh            # download if missing
#   ./packaging/fetch-vendor.sh --force    # download again
set -euo pipefail

BOOTSTRAP_VERSION="5.3.3"
ICONS_VERSION="1.11.3"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENDOR="$ROOT/web/public/assets/vendor"
FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

if [ "$FORCE" = 0 ] && [ -f "$VENDOR/bootstrap/css/bootstrap.min.css" ] \
    && [ -f "$VENDOR/bootstrap-icons/font/bootstrap-icons.min.css" ]; then
    echo "Vendor files already present (use --force to download again)."
    exit 0
fi

for tool in curl unzip; do
    command -v "$tool" >/dev/null || { echo "$tool is required" >&2; exit 1; }
done
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "Downloading Bootstrap $BOOTSTRAP_VERSION ..."
curl -fsSL -o "$TMP/bootstrap.zip" \
    "https://github.com/twbs/bootstrap/releases/download/v$BOOTSTRAP_VERSION/bootstrap-$BOOTSTRAP_VERSION-dist.zip"
echo "Downloading Bootstrap Icons $ICONS_VERSION ..."
curl -fsSL -o "$TMP/icons.zip" \
    "https://github.com/twbs/icons/releases/download/v$ICONS_VERSION/bootstrap-icons-$ICONS_VERSION.zip"
unzip -q "$TMP/bootstrap.zip" -d "$TMP"
unzip -q "$TMP/icons.zip" -d "$TMP"

B="$TMP/bootstrap-$BOOTSTRAP_VERSION-dist"
I="$TMP/bootstrap-icons-$ICONS_VERSION/font"
LICENSES="$(cd "$VENDOR" && pwd)"

# Keep the license files (they are maintained in this repository).
mkdir -p "$TMP/keep"
cp "$VENDOR/bootstrap/LICENSE" "$TMP/keep/bootstrap-LICENSE" 2>/dev/null || true
cp "$VENDOR/bootstrap-icons/LICENSE" "$TMP/keep/icons-LICENSE" 2>/dev/null || true

rm -rf "$VENDOR/bootstrap" "$VENDOR/bootstrap-icons"
mkdir -p "$VENDOR/bootstrap/css" "$VENDOR/bootstrap/js" "$VENDOR/bootstrap-icons/font/fonts"
cp "$B/css/bootstrap.min.css" "$B/css/bootstrap.min.css.map" "$VENDOR/bootstrap/css/"
cp "$B/js/bootstrap.bundle.min.js" "$B/js/bootstrap.bundle.min.js.map" "$VENDOR/bootstrap/js/"
cp "$I/bootstrap-icons.min.css" "$VENDOR/bootstrap-icons/font/"
cp "$I/fonts/bootstrap-icons.woff2" "$I/fonts/bootstrap-icons.woff" "$VENDOR/bootstrap-icons/font/fonts/"
cp "$TMP/keep/bootstrap-LICENSE" "$VENDOR/bootstrap/LICENSE" 2>/dev/null || true
cp "$TMP/keep/icons-LICENSE" "$VENDOR/bootstrap-icons/LICENSE" 2>/dev/null || true

cat > "$LICENSES/VERSIONS" <<EOF
bootstrap $BOOTSTRAP_VERSION
bootstrap-icons $ICONS_VERSION
EOF
if command -v sha256sum >/dev/null; then
    SHA="sha256sum"
else
    SHA="shasum -a 256"  # macOS
fi
(cd "$VENDOR" && find bootstrap bootstrap-icons -type f | sort | xargs $SHA > SHA256SUMS)

echo "Done. Files are in $VENDOR"
