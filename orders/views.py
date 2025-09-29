from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Order
from .serializers import OrderSerializer


class Orders(APIView):
    
    def get(self, request):
        queryset = Order.objects.all().order_by("-created_at")
        serializer = OrderSerializer(queryset, many=True)
        return Response(
            data=serializer.data,
            status=200,
        )
