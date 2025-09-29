from django.test import TestCase
from django.urls import reverse

from .models import Order, OrderItem, Product


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
			defaults={"price": 150},
		)

		self.assertEqual(product.sku, "LOREM1")
		self.assertEqual(product.price, 150)


class OrderItemTests(TestCase):
	def test_links_order_and_product_with_quantity(self):
		order = Order.objects.create(client="Beta LLC")
		product, _ = Product.objects.update_or_create(
			sku="LOREM2",
			defaults={"price": 250},
		)

		order_item = OrderItem.objects.create(order=order, product=product, quantity=3)

		self.assertEqual(order_item.quantity, 3)
		self.assertIn(product, order.products.all())
		self.assertEqual(
			order.products.through.objects.get(order=order, product=product).quantity,
			3,
		)


class OrderViewTests(TestCase):
	def test_orders_endpoint_returns_orders(self):
		Order.objects.create(client="Gamma Inc")

		response = self.client.get(reverse("orders:orders"))

		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertIn("orders", payload)
		self.assertGreaterEqual(len(payload["orders"]), 1)
		self.assertEqual(payload["orders"][0]["client"], "Gamma Inc")
