# PB POS System

A Django-based Point of Sale (POS) system with inventory management, order processing, delivery tracking, and reporting.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (fast Python package manager)
- MySQL Server

---

## Setup & Run (using uv)

### 1. Install uv

```powershell
pip install uv
```

### 2. Clone the repository

```bash
git clone https://github.com/memsa771-hub/Pb-pos-active.git
cd Pb-pos-active
```

### 3. Create virtual environment and install dependencies

```bash
uv venv
uv pip install -e .
```

### 4. Activate the virtual environment

**Windows (PowerShell):**
```powershell
.venv\Scripts\activate
```

**Linux / macOS:**
```bash
source .venv/bin/activate
```

### 5. Configure the database

Create a MySQL database named `pos_db`, then copy the environment template:

```bash
cp .env.example .env
```

Edit `.env` with your database credentials:

```env
DB_NAME=pos_db
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=3306
```

For local development you can leave `DEBUG=True` (default). Production values are set via `.env` — see [Production deployment](#production-deployment-ubuntu--caddy) below.

### 6. Run database migrations

```bash
python manage.py migrate
```

### 7. Create a superuser (admin account)

```bash
python manage.py createsuperuser
```

### 8. Start the development server

```bash
python manage.py runserver
```

Open your browser at **http://127.0.0.1:8000**

---

## Production deployment (Ubuntu + Caddy)

Target example: **https://cbk.pik-bug.shop** on Ubuntu with Caddy, Gunicorn, and MySQL.

### Quick deploy (one command on the server)

SSH into the server, then run (replace passwords):

```bash
DB_PASSWORD='YourDbPassword123!' \
ADMIN_PASSWORD='YourAdminPassword123!' \
bash -c "$(curl -fsSL https://raw.githubusercontent.com/memsa771-hub/Pb-pos-active/main/deploy/ubuntu-deploy.sh)"
```

Or clone first and run locally on the server:

```bash
git clone https://github.com/memsa771-hub/Pb-pos-active.git
cd Pb-pos-active
DB_PASSWORD='YourDbPassword123!' \
ADMIN_PASSWORD='YourAdminPassword123!' \
sudo bash deploy/ubuntu-deploy.sh
```

The script installs Python, MySQL, Caddy, clones the app to `/var/www/pb-pos`, writes `.env`, runs migrations, starts Gunicorn, and configures HTTPS.

Optional variables:

| Variable | Default |
|----------|---------|
| `DOMAIN` | `cbk.pik-bug.shop` |
| `ADMIN_USERNAME` | `admin` |
| `ADMIN_EMAIL` | `admin@example.com` |
| `APP_DIR` | `/var/www/pb-pos` |

Example config files are in `deploy/` (`Caddyfile.example`, `pb-pos.service.example`).

### After deployment

```bash
sudo journalctl -u pb-pos -f          # app logs
sudo systemctl restart pb-pos         # restart app
sudo systemctl reload caddy           # reload Caddy
```

To deploy code updates:

```bash
cd /var/www/pb-pos
sudo -u posapp git pull
sudo -u posapp bash -lc 'source .venv/bin/activate && uv pip install -e . && python manage.py migrate && python manage.py collectstatic --noinput'
sudo systemctl restart pb-pos
```

---

## Features

- POS order processing (Dine In, Takeaway, Delivery)
- Inventory management with categories, items, and purchases
- Recipe-based products
- Discount codes
- Delivery person management with commission tracking
- Sales reports and daily end-of-day summaries
- Role-based user access control
- Kitchen view
- REST API (Django REST Framework)

---

## Tech Stack

| Layer      | Technology                     |
|------------|-------------------------------|
| Backend    | Django 4.2, Django REST Framework |
| Database   | MySQL                         |
| Frontend   | Bootstrap 5, jQuery           |
| Auth       | Django Auth + JWT (SimpleJWT) |
| Package Mgr| uv                            |
