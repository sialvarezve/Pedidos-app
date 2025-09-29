from rest_framework import serializers

from .models import Order


class OrderSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ["id", "client", "created_at", "products", "total_amount"]
        read_only_fields = ["id", "created_at"]

    def get_products(self, order):
        items = order.orderitem_set.all()
        return [
            {
                "sku": item.product.sku,
                "title": item.product.title,
                "price": item.product.price,
                "quantity": item.quantity,
            }
            for item in items
        ]

    def get_total_amount(self, order):
        items = order.orderitem_set.all()
        total = sum(item.product.price * item.quantity for item in items)
        return round(float(total), 2)
