#!/usr/bin/env bash
# Install, upgrade or remove NetUSBFlash on Raspberry Pi OS.
#
#   sudo ./packaging/install.sh                 # install or upgrade
#   sudo ./packaging/install.sh --no-firewall   # skip the nftables rules
#   sudo ./packaging/install.sh --uninstall     # remove the program, keep data
#   sudo ./packaging/install.sh --uninstall --purge   # also delete all data
set -euo pipefail

APP_DIR=/opt/netusbflash
ETC_DIR=/etc/netusbflash
LIB_DIR=/var/lib/netusbflash
GROUP=netusbflash
SRC="$(cd "$(dirname "$0")/.." && pwd)"

MODE=install
PURGE=0
FIREWALL=1
BOOT_CONFIG=1
REBOOT_NEEDED=0

usage() {
    sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'
    echo
    echo "Options: --upgrade  --uninstall  --purge  --no-firewall  --skip-boot-config  -h"
}

while [ $# -gt 0 ]; do
    case "$1" in
        --upgrade) MODE=install ;;
        --uninstall) MODE=uninstall ;;
        --purge) PURGE=1 ;;
        --no-firewall) FIREWALL=0 ;;
        --skip-boot-config) BOOT_CONFIG=0 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
    esac
    shift
done

info() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mWarning:\033[0m %s\n' "$*" >&2; }
die() { printf '\033[1;31mError:\033[0m %s\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "Please run as root: sudo $0 $*"

pi_model() {
    tr -d '\0' < /proc/device-tree/model 2>/dev/null || echo "unknown"
}

check_system() {
    [ -r /etc/os-release ] || die "Cannot detect the operating system."
    . /etc/os-release
    case "${ID:-}:${ID_LIKE:-}" in
        debian:*|raspbian:*|*:*debian*) ;;
        *) die "Raspberry Pi OS (Debian based) is required, found: ${PRETTY_NAME:-unknown}" ;;
    esac
    local model
    model="$(pi_model)"
    info "Detected: $model, ${PRETTY_NAME:-}"
    case "$model" in
        *"Raspberry Pi 5"*|*"Raspberry Pi 4"*|*"Zero 2"*|*"Compute Module 4"*|*"Compute Module 5"*) ;;
        *"Raspberry Pi 500"*|*"Raspberry Pi 400"*)
            warn "The $model has no USB device (OTG) port. The USB stick emulation will not work." ;;
        *"Raspberry Pi 3"*|*"Raspberry Pi 2"*|*"Model B"*)
            warn "The $model cannot act as a USB device. The USB stick emulation will not work." ;;
        *)
            warn "Unknown or non-Raspberry Pi hardware. The USB stick emulation may not work." ;;
    esac
}

install_packages() {
    info "Installing packages ..."
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -q
    apt-get install -y -q --no-install-recommends \
        python3 python3-cryptography \
        nginx php-fpm php-curl php-mbstring \
        rclone exfatprogs dosfstools fdisk util-linux \
        openssh-client sshpass \
        nftables avahi-daemon openssl curl ca-certificates
}

fetch_vendor() {
    if [ ! -f "$SRC/web/public/assets/vendor/bootstrap/css/bootstrap.min.css" ]; then
        info "Bootstrap is not bundled yet, downloading it ..."
        "$SRC/packaging/fetch-vendor.sh"
    fi
}

copy_files() {
    info "Copying program files to $APP_DIR ..."
    install -d -m 0755 "$APP_DIR"
    rm -rf "$APP_DIR/daemon.new" "$APP_DIR/web.new"
    cp -a "$SRC/daemon" "$APP_DIR/daemon.new"
    cp -a "$SRC/web" "$APP_DIR/web.new"
    rm -rf "$APP_DIR/daemon.new/tests" "$APP_DIR/web.new/tests" "$APP_DIR/web.new/dev-router.php"
    find "$APP_DIR/daemon.new" -name '__pycache__' -prune -exec rm -rf {} +
    rm -rf "$APP_DIR/daemon" "$APP_DIR/web"
    mv "$APP_DIR/daemon.new" "$APP_DIR/daemon"
    mv "$APP_DIR/web.new" "$APP_DIR/web"
    install -m 0644 "$SRC/VERSION" "$APP_DIR/VERSION"
    chown -R root:root "$APP_DIR"
    chmod -R go-w "$APP_DIR"

    cat > /usr/local/bin/netusbflash-cli <<EOF
#!/bin/sh
exec env PYTHONPATH=$APP_DIR/daemon /usr/bin/python3 -m netusbflash.cli "\$@"
EOF
    chmod 0755 /usr/local/bin/netusbflash-cli
}

setup_group() {
    getent group "$GROUP" >/dev/null || groupadd --system "$GROUP"
    usermod -a -G "$GROUP" www-data
    install -d -m 0750 -o root -g root "$ETC_DIR" "$LIB_DIR"
}

boot_config_file() {
    if [ -f /boot/firmware/config.txt ]; then
        echo /boot/firmware/config.txt
    elif [ -f /boot/config.txt ]; then
        echo /boot/config.txt
    fi
}

enable_gadget_mode() {
    [ "$BOOT_CONFIG" = 1 ] || { warn "Skipping boot configuration (--skip-boot-config)."; return; }
    local cfg
    cfg="$(boot_config_file)"
    if [ -z "$cfg" ]; then
        warn "No config.txt found. Add 'dtoverlay=dwc2,dr_mode=peripheral' to your boot configuration by hand."
        return
    fi
    if ! grep -Eq '^[[:space:]]*dtoverlay=dwc2' "$cfg"; then
        info "Enabling USB device mode in $cfg ..."
        cp "$cfg" "$cfg.netusbflash.bak"
        printf '\n# NetUSBFlash: USB device (gadget) mode\n[all]\ndtoverlay=dwc2,dr_mode=peripheral\n' >> "$cfg"
        REBOOT_NEEDED=1
    fi
    if [ ! -f /etc/modules-load.d/netusbflash.conf ]; then
        printf 'dwc2\nlibcomposite\n' > /etc/modules-load.d/netusbflash.conf
        REBOOT_NEEDED=1
    fi
    modprobe libcomposite 2>/dev/null || true
}

create_certificate() {
    local dir="$ETC_DIR/tls"
    [ -f "$dir/cert.pem" ] && return
    info "Creating a self-signed HTTPS certificate ..."
    install -d -m 0750 "$dir"
    local host
    host="$(hostname)"
    openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \
        -keyout "$dir/key.pem" -out "$dir/cert.pem" \
        -subj "/CN=$host.local" \
        -addext "subjectAltName=DNS:$host.local,DNS:$host,DNS:localhost,IP:127.0.0.1" >/dev/null 2>&1
    chmod 0600 "$dir/key.pem"
}

php_fpm_socket() {
    local dir version
    for dir in /etc/php/*/fpm; do
        [ -d "$dir" ] || continue
        version="$(basename "$(dirname "$dir")")"
    done
    [ -n "${version:-}" ] || die "PHP-FPM was not found."
    echo "/run/php/php$version-fpm.sock|php$version-fpm"
}

configure_web() {
    info "Configuring nginx and PHP-FPM ..."
    local fpm sock service
    fpm="$(php_fpm_socket)"
    sock="${fpm%%|*}"
    service="${fpm##*|}"
    install -m 0644 "$SRC/packaging/nginx-lan-only.conf" "$ETC_DIR/nginx-lan-only.conf"
    sed "s#__PHP_FPM_SOCK__#$sock#" "$SRC/packaging/nginx-site.conf" > /etc/nginx/sites-available/netusbflash
    ln -sf /etc/nginx/sites-available/netusbflash /etc/nginx/sites-enabled/netusbflash
    rm -f /etc/nginx/sites-enabled/default
    nginx -t -q || die "nginx configuration test failed."
    # Restart PHP-FPM so www-data picks up its new group membership.
    systemctl enable -q "$service"
    systemctl restart "$service"
    systemctl enable -q nginx
    systemctl restart nginx
}

configure_services() {
    info "Installing the systemd service ..."
    install -m 0644 "$SRC/packaging/netusbflash.service" /etc/systemd/system/netusbflash.service
    if [ "$FIREWALL" = 1 ]; then
        install -m 0644 "$SRC/packaging/firewall.nft" "$ETC_DIR/firewall.nft"
        install -m 0644 "$SRC/packaging/netusbflash-firewall.service" /etc/systemd/system/netusbflash-firewall.service
    fi
    systemctl daemon-reload
    if [ "$FIREWALL" = 1 ]; then
        systemctl enable -q netusbflash-firewall
        systemctl restart netusbflash-firewall
    fi
    systemctl enable -q avahi-daemon 2>/dev/null || true
    systemctl enable -q netusbflash
    systemctl restart netusbflash
}

print_summary() {
    local code="" i
    for i in $(seq 1 30); do
        [ -S /run/netusbflash/api.sock ] && break
        sleep 1
    done
    [ -f "$ETC_DIR/setup-token" ] && code="$(cat "$ETC_DIR/setup-token")"
    echo
    info "NetUSBFlash $(cat "$APP_DIR/VERSION") installed."
    echo "Open https://$(hostname).local (or https://<IP address>) in your browser."
    if [ -n "$code" ]; then
        echo "Setup code: $code"
        echo "(show it again with: sudo netusbflash-cli setup show-code)"
    fi
    if [ "$REBOOT_NEEDED" = 1 ]; then
        echo
        warn "USB device mode was enabled. Please reboot once: sudo reboot"
    fi
}

uninstall() {
    info "Removing NetUSBFlash ..."
    systemctl disable --now netusbflash 2>/dev/null || true
    if [ -x /usr/local/bin/netusbflash-cli ]; then
        /usr/local/bin/netusbflash-cli usb teardown 2>/dev/null || true
    fi
    systemctl disable --now netusbflash-firewall 2>/dev/null || true
    rm -f /etc/systemd/system/netusbflash.service /etc/systemd/system/netusbflash-firewall.service
    systemctl daemon-reload
    rm -f /etc/nginx/sites-enabled/netusbflash /etc/nginx/sites-available/netusbflash
    systemctl reload nginx 2>/dev/null || true
    rm -f /usr/local/bin/netusbflash-cli /etc/modules-load.d/netusbflash.conf
    rm -rf "$APP_DIR"
    if [ "$PURGE" = 1 ]; then
        info "Deleting all settings and data (--purge) ..."
        rm -rf "$ETC_DIR" "$LIB_DIR"
        gpasswd -d www-data "$GROUP" >/dev/null 2>&1 || true
        groupdel "$GROUP" 2>/dev/null || true
    else
        echo "Settings and data are kept in $ETC_DIR and $LIB_DIR (remove with --uninstall --purge)."
    fi
    echo "The line 'dtoverlay=dwc2,dr_mode=peripheral' in config.txt was left in place."
    info "Done."
}

if [ "$MODE" = uninstall ]; then
    uninstall
    exit 0
fi

check_system
install_packages
fetch_vendor
setup_group
copy_files
enable_gadget_mode
create_certificate
configure_web
configure_services
print_summary
