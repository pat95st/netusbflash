#!/usr/bin/env bash
# Download Bootstrap and Bootstrap Icons into web/public/assets/vendor.
#
# The web UI loads these files from the Pi itself (no CDN), so it also works
# without internet access. Run this once on a machine with internet access and
# commit the result, or let install.sh run it on the Pi.
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

command -v curl >/dev/null || { echo "curl is required" >&2; exit 1; }
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

fetch() {
    local name="$1" version="$2"
    echo "Downloading $name $version ..."
    curl -fsSL "https://registry.npmjs.org/$name/-/$name-$version.tgz" -o "$TMP/$name.tgz"
    mkdir -p "$TMP/$name"
    tar -xzf "$TMP/$name.tgz" -C "$TMP/$name"
}

fetch bootstrap "$BOOTSTRAP_VERSION"
fetch bootstrap-icons "$ICONS_VERSION"

rm -rf "$VENDOR/bootstrap" "$VENDOR/bootstrap-icons"
mkdir -p "$VENDOR/bootstrap/css" "$VENDOR/bootstrap/js" "$VENDOR/bootstrap-icons/font/fonts"

B="$TMP/bootstrap/package"
cp "$B/dist/css/bootstrap.min.css" "$B/dist/css/bootstrap.min.css.map" "$VENDOR/bootstrap/css/"
cp "$B/dist/js/bootstrap.bundle.min.js" "$B/dist/js/bootstrap.bundle.min.js.map" "$VENDOR/bootstrap/js/"
cp "$B/LICENSE" "$VENDOR/bootstrap/LICENSE"

I="$TMP/bootstrap-icons/package"
cp "$I/font/bootstrap-icons.min.css" "$VENDOR/bootstrap-icons/font/"
cp "$I/font/fonts/bootstrap-icons.woff2" "$I/font/fonts/bootstrap-icons.woff" "$VENDOR/bootstrap-icons/font/fonts/"
cp "$I/LICENSE" "$VENDOR/bootstrap-icons/LICENSE"

cat > "$VENDOR/VERSIONS" <<EOF
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
