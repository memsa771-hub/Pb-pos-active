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

Create a MySQL database named `pos_db` and update the credentials in `posproject/settings.py` if needed:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'pos_db',
        'USER': 'root',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

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
