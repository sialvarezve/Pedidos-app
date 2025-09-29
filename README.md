# Pedidos-app

A minimal Django project configured with SQLite for local development. It manage orders of products asynchronously.

## Getting started

Requires **Python 3.13**.

1. Create and activate a virtual environment (skip if you already have one).
2. Install dependencies.
3. Run migrations and start the development server.

### Setup commands

```bash
python -m venv .env
source .env/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

The application uses the default SQLite database located at `db.sqlite3` in the project root.

## Project structure highlights

- `orders/`: Custom Django app for managing order-related logic.
