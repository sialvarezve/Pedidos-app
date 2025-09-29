from django.db import models


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

	def __str__(self) -> str:
		return f"{self.sku} (${self.price})"


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
