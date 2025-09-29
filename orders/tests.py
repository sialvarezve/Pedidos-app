import json

from datetime import datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.urls import reverse
from django.utils.dateparse import parse_datetime
from django.utils import timezone

from .models import Order, OrderItem, Product


def _successful_catalog_response(*, price: int, title: str) -> MagicMock:
	response = MagicMock()
	response.status_code = 200
	response.json.return_value = {
		"title": title,
		"price": price,
		"description": f"Description for {title}",
		"category": "General",
	}
	return response


class OrderModelTests(TestCase):
	def test_creates_order_with_client_and_timestamp(self):
		Order.objects.filter(client="Acme Corp").delete()
		order = Order.objects.create(client="Acme Corp")

		self.assertEqual(order.client, "Acme Corp")
		self.assertIsNotNone(order.created_at)


class ProductModelTests(TestCase):
	def test_creates_product_with_sku_and_price(self):
		product, _ = Product.objects.update_or_create(
			sku="LOREM1",
			defaults={
				"price": 150,
				"title": "Lorem Ipsum",
				"description": "Sample description",
				"category": "Category A",
			},
		)

		self.assertEqual(product.sku, "LOREM1")
		self.assertEqual(product.price, 150)
		self.assertEqual(product.title, "Lorem Ipsum")
		self.assertEqual(product.description, "Sample description")
		self.assertEqual(product.category, "Category A")


class OrderItemTests(TestCase):
	def test_links_order_and_product_with_quantity(self):
		order = Order.objects.create(client="Beta LLC")
		product, _ = Product.objects.update_or_create(
			sku="LOREM2",
			defaults={
				"price": 250,
				"title": "Product P",
				"description": "Product P description",
				"category": "Category B",
			},
		)

		order_item = OrderItem.objects.create(
			order=order,
			product=product,
			quantity=3,
		)

		self.assertEqual(order_item.pk, (order.pk, product.pk))
		self.assertEqual(order_item.quantity, 3)
		self.assertIn(product, order.products.all())
		through_model = order.products.through
		item = through_model.objects.get(order=order, product=product)
		self.assertEqual(item.quantity, 3)


class OrderViewTests(TestCase):
	def test_orders_endpoint_returns_orders(self):
		Order.objects.create(client="Gamma Inc")

		response = self.client.get(reverse("orders:orders"))

		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertIn("orders", payload)
		self.assertGreaterEqual(len(payload["orders"]), 1)
		self.assertEqual(payload["orders"][0]["client"], "Gamma Inc")

	def test_orders_endpoint_creates_order(self):
		with patch("orders.models.requests.get") as mock_get:
			mock_get.side_effect = [
				_successful_catalog_response(price=10, title="Product P001"),
				_successful_catalog_response(price=20, title="Product P002"),
			]

			payload = {
				"id": 123,
				"cliente": "ACME Corp",
				"productos": [
					{"sku": "P001", "cantidad": 3, "precio_unitario": 10},
					{"sku": "P002", "cantidad": 5, "precio_unitario": 20},
				],
				"fecha": "2025-01-01T10:30:00Z",
			}

			response = self.client.post(
				reverse("orders:orders"),
				data=json.dumps(payload),
				content_type="application/json",
			)

		self.assertEqual(response.status_code, 201)
		body = response.json()
		self.assertIn("order", body)
		self.assertEqual(body["order"]["id"], 123)
		self.assertEqual(body["order"]["client"], "ACME Corp")
		self.assertEqual(body["order"]["created_at"], "2025-01-01T10:30:00Z")

		order = Order.objects.get(pk=123)
		self.assertEqual(order.client, "ACME Corp")
		through_model = order.products.through
		self.assertEqual(through_model.objects.filter(order=order).count(), 2)

		product_one = Product.objects.get(sku="P001")
		self.assertEqual(product_one.price, 10)
		self.assertEqual(product_one.title, "Product P001")
		item = through_model.objects.get(order=order, product=product_one)
		self.assertEqual(item.quantity, 3)

		self.assertTrue(Product.objects.filter(sku="P002", price=20).exists())
		parsed_fecha_raw = parse_datetime(payload["fecha"])
		self.assertIsNotNone(parsed_fecha_raw)
		assert parsed_fecha_raw is not None
		parsed_fecha: datetime = parsed_fecha_raw
		if timezone.is_naive(parsed_fecha):
			parsed_fecha = timezone.make_aware(parsed_fecha, timezone.get_current_timezone())
		order.refresh_from_db()
		self.assertEqual(order.created_at, parsed_fecha)

	def test_orders_endpoint_merges_products_for_existing_order(self):
		with patch("orders.models.requests.get") as mock_get:
			mock_get.side_effect = [
				_successful_catalog_response(price=10, title="Product P001"),
				_successful_catalog_response(price=20, title="Product P002"),
			]

			initial_payload = {
				"id": 200,
				"cliente": "ACME Corp",
				"productos": [
					{"sku": "P001", "cantidad": 3, "precio_unitario": 10},
					{"sku": "P002", "cantidad": 2, "precio_unitario": 20},
				],
				"fecha": "2025-01-05T12:00:00Z",
			}

			response = self.client.post(
				reverse("orders:orders"),
				data=json.dumps(initial_payload),
				content_type="application/json",
			)

		self.assertEqual(response.status_code, 201)
		order = Order.objects.get(pk=200)
		original_created_at = order.created_at

		with patch("orders.models.requests.get") as mock_get:
			mock_get.side_effect = [
				_successful_catalog_response(price=30, title="Product P003"),
				_successful_catalog_response(price=10, title="Product P001"),
			]

			update_payload = {
				"id": 200,
				"cliente": "ACME Corp",
				"productos": [
					{"sku": "P003", "cantidad": 4, "precio_unitario": 30},
					{"sku": "P001", "cantidad": 2, "precio_unitario": 10},
				],
				"fecha": "2025-02-01T09:00:00Z",
			}

			second_response = self.client.post(
				reverse("orders:orders"),
				data=json.dumps(update_payload),
				content_type="application/json",
			)

		self.assertEqual(second_response.status_code, 201)
		order.refresh_from_db()
		self.assertEqual(order.created_at, original_created_at)
		through_model = order.products.through
		self.assertEqual(through_model.objects.filter(order=order).count(), 3)

		product_one = Product.objects.get(sku="P001")
		item_one = through_model.objects.get(order=order, product=product_one)
		self.assertEqual(item_one.quantity, 5)

		product_two = Product.objects.get(sku="P002")
		item_two = through_model.objects.get(order=order, product=product_two)
		self.assertEqual(item_two.quantity, 2)

		product_three = Product.objects.get(sku="P003")
		self.assertEqual(product_three.price, 30)
		item_three = through_model.objects.get(order=order, product=product_three)
		self.assertEqual(item_three.quantity, 4)

	def test_orders_endpoint_validation_error_returns_400(self):
		payload = {
			"cliente": "",
			"productos": [],
		}

		response = self.client.post(
			reverse("orders:orders"),
			data=json.dumps(payload),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 400)
		body = response.json()
		self.assertIn("errors", body)

	def test_orders_endpoint_rejects_price_mismatch(self):
		payload = {
			"cliente": "ACME Corp",
			"productos": [
				{"sku": "P010", "cantidad": 1, "precio_unitario": 10},
			],
		}

		with patch("orders.models.requests.get") as mock_get:
			mock_get.return_value = _successful_catalog_response(
				price=11,
				title="Product P010",
			)

			response = self.client.post(
				reverse("orders:orders"),
				data=json.dumps(payload),
				content_type="application/json",
			)

		self.assertEqual(response.status_code, 400)
		body = response.json()
		self.assertIn("errors", body)
		self.assertIn("productos", body["errors"])
		message = body["errors"]["productos"]
		self.assertIn("Unit price for product P010 must match 11", message)

	def test_orders_endpoint_accepts_fractional_catalog_price(self):
		payload = {
			"cliente": "ACME Corp",
			"productos": [
				{"sku": "P011", "cantidad": 1, "precio_unitario": 10.5},
			],
		}

		with patch("orders.models.requests.get") as mock_get:
			response_mock = MagicMock()
			response_mock.status_code = 200
			response_mock.json.return_value = {
				"title": "Product P011",
				"price": 10.5,
				"description": "Description for Product P011",
				"category": "General",
			}
			mock_get.return_value = response_mock

			response = self.client.post(
				reverse("orders:orders"),
				data=json.dumps(payload),
				content_type="application/json",
			)

		self.assertEqual(response.status_code, 201)
		order = Order.objects.get(client="ACME Corp")
		product = Product.objects.get(sku="P011")
		self.assertEqual(product.price, 10.5)
		through_model = order.products.through
		item = through_model.objects.get(order=order, product=product)
		self.assertEqual(item.quantity, 1)
