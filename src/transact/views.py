from rest_framework import status
from rest_framework import request, response
from rest_framework.views import APIView

from .serializers import CompositeCreationSerializer


class BulkAccountTransactionView(APIView):
    def post(self, request: request.Request) -> response.Response:
        serializer = CompositeCreationSerializer(data=request.data)
        if serializer.is_valid():
            response_data = serializer.save()
            return response.Response(response_data, status=status.HTTP_201_CREATED)
        return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
