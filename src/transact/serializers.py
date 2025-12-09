from uuid import uuid4

from django.db import transaction
from rest_framework import serializers

from .models import Account, Transaction
from .task import categorise_transactions


class AccountSerializer(serializers.ModelSerializer):
    account_id = serializers.CharField()

    class Meta:
        model = Account
        fields = ["account_id", "name", "type", "subtype", "mask"]


class TransactionSerializer(serializers.ModelSerializer):
    # Use IntegerField for the ID reference to avoid DRF validating existence immediately
    account_id = serializers.CharField()
    iso_currency_code = serializers.CharField(source="currency")
    name = serializers.CharField(source="description")

    class Meta:
        model = Transaction
        fields = ["transaction_id", "account_id", "amount", "iso_currency_code", "date", "merchant_name", "name"]


class TopCategorySerializer(serializers.Serializer):
    """Serializer for top spending categories."""

    category = serializers.CharField()
    total_spend = serializers.DecimalField(max_digits=12, decimal_places=2)
    transaction_count = serializers.IntegerField()


class ProcessingStatusSerializer(serializers.Serializer):
    """Serializer for transaction processing status breakdown."""

    pending = serializers.IntegerField()
    processing = serializers.IntegerField()
    completed = serializers.IntegerField()
    failed = serializers.IntegerField()


class DateRangeSerializer(serializers.Serializer):
    """Serializer for date range."""

    start = serializers.DateField()
    end = serializers.DateField()


class MetricsSerializer(serializers.Serializer):
    """Serializer for account metrics."""

    total_transactions = serializers.IntegerField()
    total_spend = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_income = serializers.DecimalField(max_digits=12, decimal_places=2)
    net = serializers.DecimalField(max_digits=12, decimal_places=2)


class AccountSummarySerializer(serializers.Serializer):
    """Serializer for account summary with metrics, categories, and processing status."""

    account_id = serializers.CharField()
    date_range = DateRangeSerializer()
    metrics = MetricsSerializer()
    top_categories = TopCategorySerializer(many=True)
    processing_status = ProcessingStatusSerializer()


class CompositeCreationSerializer(serializers.Serializer):
    accounts = AccountSerializer(many=True)
    transactions = TransactionSerializer(many=True)

    def create(self, validated_data: dict) -> dict:
        """
        Create Accounts and Transactions in bulk, maintaining the relationships between them.

        :param validated_data: The validated data containing accounts and transactions.
        :return: A dictionary with created accounts and transactions.
        """
        accounts_data = validated_data.get("accounts", [])
        transactions_data = validated_data.get("transactions", [])

        request_account_ids = [account["account_id"] for account in accounts_data]
        accounts_to_create = []

        with transaction.atomic():
            # We first handle the accounts via upserts
            # In this case, insert new accounts and ignore existing ones
            existing_accounts = Account.objects.filter(account_id__in=request_account_ids)
            existing_account_ids = set(acc.account_id for acc in existing_accounts)

            for account in accounts_data:
                if account["account_id"] not in existing_account_ids:
                    accounts_to_create.append(Account(**account))

            if accounts_to_create:
                Account.objects.bulk_create(accounts_to_create)

            # Bulk create the transactions now that all necessary accounts exist
            batch_id = str(uuid4())
            Transaction.objects.bulk_create([Transaction(**data, batch_id=batch_id) for data in transactions_data])

        # Trigger asynchronous categorization for this batch
        categorise_transactions.delay(batch_id=batch_id)

        return {
            "total_transactions": len(accounts_data + transactions_data),
            "batch_id": batch_id,
        }
