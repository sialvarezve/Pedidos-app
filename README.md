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

## API endpoints

Base URL: `http://localhost:8000/orders/`

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/orders/` | Returns all orders, including product details and total amount. |
| `POST` | `/orders/` | Creates or updates an order and its line items. |

### `GET /orders/`

Example response:

```json
{
	"orders": [
		{
			"id": 123,
			"client": "ACME Corp",
			"created_at": "2025-01-01T10:30:00Z",
			"products": [
				{"sku": "P001", "title": "Product P001", "price": 10.0, "quantity": 3},
				{"sku": "P002", "title": "Product P002", "price": 20.0, "quantity": 5}
			],
			"total_amount": 130.0
		}
	]
}
```

### `POST /orders/`

Sample request body:

```json
{
	"id": 123,
	"cliente": "ACME Corp",
	"productos": [
		{"sku": "P001", "cantidad": 3, "precio_unitario": 10},
		{"sku": "P002", "cantidad": 5, "precio_unitario": 20}
	],
	"fecha": "2025-01-01T10:30:00Z"
}
```

Responses:

- **201 Created** – order accepted; response mirrors `GET` structure under `order` key.
- **400 Bad Request** – validation errors, returned under `errors` key.
- **500 Internal Server Error** – unexpected failure after retries.

## Project structure highlights

- `orders/`: Custom Django app for managing order-related logic.
