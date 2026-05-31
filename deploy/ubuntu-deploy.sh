#!/usr/bin/env bash
# PB POS — Ubuntu server deploy (Caddy + Gunicorn + MySQL)
#
# Run on a fresh Ubuntu 22.04/24.04 server as root:
#   curl -fsSL https://raw.githubusercontent.com/memsa771-hub/Pb-pos-active/main/deploy/ubuntu-deploy.sh | bash
# Or after cloning:
#   sudo bash deploy/ubuntu-deploy.sh
#
# Edit the variables below before running.

set -euo pipefail

# --- Configuration (edit these) ---
DOMAIN="${DOMAIN:-cbk.pik-bug.shop}"
APP_USER="${APP_USER:-posapp}"
APP_DIR="${APP_DIR:-/var/www/pb-pos}"
REPO_URL="${REPO_URL:-https://github.com/memsa771-hub/Pb-pos-active.git}"
BRANCH="${BRANCH:-main}"

DB_NAME="${DB_NAME:-pos_db}"
DB_USER="${DB_USER:-posuser}"
DB_PASSWORD="${DB_PASSWORD:-}"          # required — set before running
SECRET_KEY="${SECRET_KEY:-}"            # auto-generated if empty

ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@example.com}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"    # required — set before running

GUNICORN_WORKERS="${GUNICORN_WORKERS:-3}"
GUNICORN_PORT="${GUNICORN_PORT:-8000}"

# --- Helpers ---
log() { echo "[deploy] $*"; }
die() { echo "[deploy] ERROR: $*" >&2; exit 1; }

require_root() {
    [[ "${EUID:-$(id -u)}" -eq 0 ]] || die "Run as root: sudo bash deploy/ubuntu-deploy.sh"
}

generate_secret() {
    python3 -c "import secrets; print(secrets.token_urlsafe(50))"
}

# --- Pre-flight ---
require_root

if [[ -z "$DB_PASSWORD" ]]; then
    die "Set DB_PASSWORD before running, e.g.: DB_PASSWORD='your-db-pass' ADMIN_PASSWORD='your-admin-pass' bash deploy/ubuntu-deploy.sh"
fi
if [[ -z "$ADMIN_PASSWORD" ]]; then
    die "Set ADMIN_PASSWORD before running."
fi
if [[ -z "$SECRET_KEY" ]]; then
    SECRET_KEY="$(generate_secret)"
    log "Generated SECRET_KEY"
fi

export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a
export UCF_FORCE_CONFFNEW=1

# --- System packages ---
log "Installing system packages..."
apt-get update -qq
apt-get upgrade -y -qq \
    -o Dpkg::Options::="--force-confdef" \
    -o Dpkg::Options::="--force-confold" || true
apt-get install -y -qq \
    python3 python3-venv python3-dev \
    build-essential pkg-config \
    default-libmysqlclient-dev \
    mysql-server \
    git curl ufw

# uv (Python package manager) — also installs Python 3.12 on Ubuntu 22.04
if ! command -v uv >/dev/null 2>&1; then
    log "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh
fi
export PATH="/usr/local/bin:${PATH}"

# Caddy
if ! command -v caddy >/dev/null 2>&1; then
    log "Installing Caddy..."
    apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
        | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
        | tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
    apt-get update -qq
    apt-get install -y -qq caddy
fi

# Firewall
ufw allow OpenSSH >/dev/null 2>&1 || true
ufw allow 80/tcp >/dev/null 2>&1 || true
ufw allow 443/tcp >/dev/null 2>&1 || true
echo "y" | ufw enable >/dev/null 2>&1 || true

# --- MySQL ---
log "Configuring MySQL database..."
mysql -e "CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -e "CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';"
mysql -e "GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'localhost';"
mysql -e "FLUSH PRIVILEGES;"

# --- App user & code ---
if ! id "$APP_USER" &>/dev/null; then
    log "Creating system user: $APP_USER"
    adduser --disabled-password --gecos "" "$APP_USER"
    usermod -aG www-data "$APP_USER"
fi

mkdir -p "$APP_DIR"
chown "$APP_USER:$APP_USER" "$APP_DIR"

if [[ -d "$APP_DIR/.git" ]]; then
    log "Updating existing repo..."
    sudo -u "$APP_USER" git -C "$APP_DIR" fetch origin
    sudo -u "$APP_USER" git -C "$APP_DIR" checkout "$BRANCH"
    sudo -u "$APP_USER" git -C "$APP_DIR" pull origin "$BRANCH"
else
    log "Cloning repository..."
    sudo -u "$APP_USER" git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

# --- .env ---
log "Writing .env..."
cat >"$APP_DIR/.env" <<EOF
SECRET_KEY=${SECRET_KEY}
DEBUG=False
ALLOWED_HOSTS=${DOMAIN},localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://${DOMAIN}

DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_HOST=localhost
DB_PORT=3306
EOF
chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
chmod 600 "$APP_DIR/.env"

# --- Python deps, migrate, static ---
log "Installing Python dependencies..."
sudo -u "$APP_USER" bash -lc "
    export PATH=\"/usr/local/bin:\$PATH\"
    cd '$APP_DIR'
    uv python install 3.12
    uv venv --python 3.12
    source .venv/bin/activate
    uv pip install -e .
"

log "Running migrations and collectstatic..."
sudo -u "$APP_USER" bash -lc "
    cd '$APP_DIR'
    source .venv/bin/activate
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
"

mkdir -p "$APP_DIR/media"
chown -R "$APP_USER:www-data" "$APP_DIR/media"
chmod 775 "$APP_DIR/media"

# --- Superuser (skip if already exists) ---
log "Creating admin user (if new)..."
sudo -u "$APP_USER" bash -lc "
    cd '$APP_DIR'
    source .venv/bin/activate
    DJANGO_SUPERUSER_PASSWORD='${ADMIN_PASSWORD}' \
    python manage.py createsuperuser \
        --noinput \
        --username '${ADMIN_USERNAME}' \
        --email '${ADMIN_EMAIL}' \
    2>/dev/null || true
"

# --- Gunicorn systemd service ---
log "Installing systemd service..."
cat >/etc/systemd/system/pb-pos.service <<EOF
[Unit]
Description=PB POS Gunicorn
After=network.target mysql.service

[Service]
User=${APP_USER}
Group=www-data
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
Environment="PATH=${APP_DIR}/.venv/bin"
ExecStart=${APP_DIR}/.venv/bin/gunicorn \\
    --workers ${GUNICORN_WORKERS} \\
    --bind 127.0.0.1:${GUNICORN_PORT} \\
    --timeout 120 \\
    posproject.wsgi:application
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable pb-pos
systemctl restart pb-pos

# --- Caddy ---
log "Configuring Caddy for ${DOMAIN}..."
cat >/etc/caddy/Caddyfile <<EOF
${DOMAIN} {
    encode gzip

    handle_path /media/* {
        root * ${APP_DIR}/media
        file_server
    }

    reverse_proxy 127.0.0.1:${GUNICORN_PORT}
}
EOF

systemctl enable caddy
systemctl reload caddy

# --- Done ---
log "Deployment complete."
echo ""
echo "  Site:    https://${DOMAIN}"
echo "  Admin:   https://${DOMAIN}/admin/"
echo "  Login:   ${ADMIN_USERNAME} / (password you set)"
echo ""
echo "  Logs:    journalctl -u pb-pos -f"
echo "  Restart: systemctl restart pb-pos"
echo ""

if curl -sf "http://127.0.0.1:${GUNICORN_PORT}/" -o /dev/null; then
    log "Gunicorn health check: OK"
else
    log "WARNING: Gunicorn did not respond on port ${GUNICORN_PORT}. Check: journalctl -u pb-pos -n 50"
fi
