import re
import requests

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable

from django.db import models, transaction
from rest_framework.exceptions import ValidationError

from .utils import normalize_timestamp


FAKESTORE_PRODUCT_URL = "https://fakestoreapi.com/products/{product_id}"


class Order(models.Model):
	client = models.CharField(max_length=128)
	created_at = models.DateTimeField(auto_now_add=True)
	products = models.ManyToManyField(
		"Product",
		through="OrderItem",
		related_name="orders",
	)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self) -> str:
		return f"Order #{self.pk} for {self.client}"


class Product(models.Model):
	sku = models.CharField(max_length=8, primary_key=True)
	price = models.IntegerField()
	title = models.CharField(max_length=128, default="")
	description = models.TextField(default="", blank=True)
	category = models.CharField(max_length=32, default="", blank=True)

	def __str__(self) -> str:
		return f"{self.sku}{self.title or ''} (${self.price})"

	@staticmethod
	def ensure(item_payload: Dict[str, Any]) -> "Product":
		sku = item_payload.get("sku")
		if not sku:
			raise ValidationError({"productos": "Each product requires an SKU."})

		unit_price = item_payload.get("precio_unitario")
		if unit_price is None:
			raise ValidationError({"productos": f"Product {sku} requires unit price."})

		digits = re.sub(r"\D", "", sku)
		if not digits:
			raise ValidationError({"productos": f"Product {sku} must include digits."})

		try:
			product_id = int(digits)
		except ValueError as exc:
			raise ValidationError(
				{"productos": f"Invalid SKU format for product {sku}."}
			) from exc

		product_attrs = {
			"sku": sku,
			"product_id": product_id,
			"unit_price": unit_price,
		}
		return Product._sync_from_catalog(**product_attrs)

	@staticmethod
	def _sync_from_catalog(**product_attrs: Any) -> "Product":
		sku = product_attrs["sku"]
		product_id = product_attrs["product_id"]
		unit_price = product_attrs["unit_price"]
		try:
			response = requests.get(
				FAKESTORE_PRODUCT_URL.format(product_id=product_id),
				timeout=5,
			)
		except requests.RequestException as exc:
			raise ValidationError(
				{"productos": f"Unable to fetch product {sku} from catalog."}
			) from exc

		if response.status_code != 200:
			raise ValidationError(
				{"productos": f"Product {sku} not found in external catalog."}
			)

		try:
			payload = response.json()
		except ValueError as exc:
			raise ValidationError(
				{"productos": "Invalid response from product catalog."}
			) from exc

		for field in ("title", "price", "description", "category"):
			if field not in payload:
				raise ValidationError(
					{"productos": "Incomplete product information received."}
				)

		try:
			request_price = Decimal(str(unit_price))
			catalog_price = Decimal(str(payload["price"]))
		except (InvalidOperation, TypeError) as exc:
			raise ValidationError(
				{"productos": f"Invalid price format for product {sku}."}
			) from exc

		if request_price != catalog_price:
			raise ValidationError(
				{
					"productos": (
						f"Unit price for product {sku} must match {catalog_price}."
					)
				}
			)

		if catalog_price != catalog_price.to_integral_value():
			raise ValidationError(
				{
					"productos": (
						f"Catalog price for product {sku} must be an integer value."
					)
				}
			)

		price_value = int(catalog_price)
		defaults = {"price": price_value}
		product, _ = Product.objects.get_or_create(sku=sku, defaults=defaults)
		updates = {
			"price": price_value,
			"title": payload["title"],
			"description": payload["description"],
			"category": payload["category"],
		}
		for field, value in updates.items():
			setattr(product, field, value)
		product.save(update_fields=list(updates.keys()))
		return product


class OrderItem(models.Model):
	order = models.ForeignKey(Order, on_delete=models.CASCADE)
	product = models.ForeignKey(Product, on_delete=models.CASCADE)
	quantity = models.PositiveIntegerField(default=1)

	class Meta:
		unique_together = ("order", "product")
		verbose_name = "Order item"
		verbose_name_plural = "Order items"

	def __str__(self) -> str:
		order_reference = getattr(self.order, "pk", None)
		return f"{self.quantity} × {self.product} for order #{order_reference or '?'}"

	@staticmethod
	@transaction.atomic
	def create_or_update_order_with_items(order_payload: Dict[str, Any]) -> Order:
        
		if not isinstance(order_payload, dict):
			raise ValidationError("Invalid payload.")

		client = order_payload.get("cliente")
		if not client:
			raise ValidationError({"cliente": "This field is required."})

		productos: Iterable[Dict[str, Any]] = order_payload.get("productos", [])
		if not productos:
			raise ValidationError({"productos": "At least one product must be provided."})

		timestamp = normalize_timestamp(order_payload.get("fecha"))

		order_id = order_payload.get("id")
		order_defaults = {"client": client}

		if order_id is None:
			order = Order.objects.create(**order_defaults)
			created = True
		else:
			order, created = Order.objects.update_or_create(
				pk=order_id,
				defaults=order_defaults,
			)

		if timestamp and created:
			Order.objects.filter(pk=order.pk).update(created_at=timestamp)
			order.created_at = timestamp

		for item_payload in productos:
			product = Product.ensure(item_payload)
			quantity = item_payload.get("cantidad")
			if quantity is None:
				message = f"Product {product.sku} requires quantity."
				raise ValidationError({"productos": message})
			try:
				quantity_int = int(quantity)
			except (TypeError, ValueError) as exc:
				message = f"Invalid quantity for product {product.sku}."
				raise ValidationError({"productos": message}) from exc
			if quantity_int <= 0:
				message = f"Quantity must be positive for product {product.sku}."
				raise ValidationError({"productos": message})

			existing_item = OrderItem.objects.filter(order=order, product=product).first()
			if existing_item:
				existing_item.quantity += quantity_int
				existing_item.save(update_fields=["quantity"])
			else:
				OrderItem.objects.create(
					order=order,
					product=product,
					quantity=quantity_int,
				)

		return order


