from django.contrib import admin

from .models import Order, OrderItem, Product


class OrderItemInline(admin.TabularInline):
	model = OrderItem
	extra = 1
	min_num = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
	list_display = ("id", "client", "created_at")
	search_fields = ("client",)
	ordering = ("-created_at",)
	inlines = (OrderItemInline,)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
	list_display = ("sku", "price")
	search_fields = ("sku",)
