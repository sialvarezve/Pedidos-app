import logging

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Order, OrderItem
from .serializers import OrderSerializer


logger = logging.getLogger(__name__)


class Orders(APIView):
	
	def get(self, request):
		try:
			queryset = Order.objects.all().order_by("-created_at")
			serializer = OrderSerializer(queryset, many=True)
			return Response(
				data={"orders": serializer.data},
				status=status.HTTP_200_OK,
			)
		except Exception:
			logger.exception("Failed to list orders")
			return Response(
				{"error": "Error retrieving orders."},
				status=status.HTTP_500_INTERNAL_SERVER_ERROR,
			)
	
	def post(self, request, attempts=0):
		__max_attempts = 4
		try:
			try:    
				order = OrderItem.create_or_update_order_with_items(request.data)
				serializer = OrderSerializer(order)
				return Response(
					data={"order": serializer.data},
					status=status.HTTP_201_CREATED,
				)	
			
			except Exception as error:
				attempts += 1
				if attempts < __max_attempts:
					logger.warning(
						f"Attempt {attempts} to create order failed: {error}. Retrying..."
					)
					return self.post(request, attempts=attempts)
				else:
					logger.error(f"All {__max_attempts} attempts to create order failed.")
					raise error
		
		except ValidationError as exc:
			return Response(
				{"errors": exc.detail},
				status=status.HTTP_400_BAD_REQUEST,
			)
		except Exception:
			logger.exception("Failed to create order")
			return Response(
				{"error": "Error creating order."},
				status=status.HTTP_500_INTERNAL_SERVER_ERROR,
			)
