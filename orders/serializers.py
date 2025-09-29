from rest_framework import serializers

from .models import Order


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["id", "client", "created_at"]
        read_only_fields = ["id", "created_at"]
