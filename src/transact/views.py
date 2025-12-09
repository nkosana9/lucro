from datetime import datetime

from rest_framework import request, response, status
from rest_framework.views import APIView

from .models import Transaction
from .serializers import AccountSummarySerializer, CompositeCreationSerializer


class BulkAccountTransactionView(APIView):
    def post(self, request: request.Request) -> response.Response:
        serializer = CompositeCreationSerializer(data=request.data)
        if serializer.is_valid():
            response_data = serializer.save()
            return response.Response(response_data, status=status.HTTP_201_CREATED)
        return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SummaryAccountView(APIView):
    def get(self, request: request.Request, account_id: str) -> response.Response:
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date") or datetime.now().date().isoformat()

        # Date validation
        if not start_date:
            return response.Response(
                {"error": "The start_date query parameter is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError as e:
            return response.Response(
                {"error": f"Invalid date format. Use YYYY-MM-DD: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST
            )
        if start_date > end_date:
            return response.Response(
                {"error": "start_date cannot be after end_date"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Get account summary data from the model manager
        summary_data = Transaction.objects.account_summary(
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
        )

        # Serialize and return the data
        serializer = AccountSummarySerializer(data=summary_data)
        if serializer.is_valid():
            return response.Response(serializer.data, status=status.HTTP_200_OK)
        return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
