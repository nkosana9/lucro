from datetime import date
from decimal import Decimal

from django.db import models
from django.db.models import Count, Q, Sum
from django.utils.translation import gettext_lazy as _


class Account(models.Model):
    account_id = models.CharField(primary_key=True, max_length=100)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50)
    subtype = models.CharField(max_length=50, null=True, blank=True)
    mask = models.CharField(max_length=10, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class TransactionManager(models.Manager):
    def account_summary(self, account_id: str, start_date: date, end_date: date) -> dict:
        """
        Return the account summary for the given account and date range.

        :param account_id: The account ID to summarize.
        :param start_date: The start date for the summary (inclusive).
        :param end_date: The end date for the summary (inclusive).
        :return: A dictionary containing the account summary.
        """
        applicable_transactions = self.filter(
            account_id=account_id,
            date__date__gte=start_date,
            date__date__lte=end_date,
        )

        metrics = applicable_transactions.aggregate(
            total_transactions=Count("transaction_id"),
            total_spend=Sum("amount", filter=Q(amount__lt=0)),
            total_income=Sum("amount", filter=Q(amount__gt=0)),
        )

        total_spend = abs(metrics["total_spend"] or Decimal("0.00"))
        total_income = metrics["total_income"] or Decimal("0.00")

        top_categories_data = (
            applicable_transactions.filter(category__isnull=False)
            .values("category")
            .annotate(
                total_spend=Sum("amount", filter=Q(amount__lt=0)),
                transaction_count=Count("transaction_id"),
            )
            .order_by("-total_spend")[:5]
        )

        top_categories = [
            {
                "category": cat["category"],
                "total_spend": abs(cat["total_spend"] or Decimal("0.00")),
                "transaction_count": cat["transaction_count"],
            }
            for cat in top_categories_data
        ]

        status_breakdown = applicable_transactions.values("ingestion_status").annotate(count=Count("transaction_id"))

        processing_status = {
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0,
        }

        for status_item in status_breakdown:
            status_key = status_item["ingestion_status"]
            if status_key in processing_status:
                processing_status[status_key] = status_item["count"]

        return {
            "account_id": account_id,
            "date_range": {"start": start_date, "end": end_date},
            "metrics": {
                "total_transactions": metrics["total_transactions"] or 0,
                "total_spend": total_spend,
                "total_income": total_income,
                "net": total_income - total_spend,
            },
            "top_categories": top_categories,
            "processing_status": processing_status,
        }


class Transaction(models.Model):
    objects = TransactionManager()

    class IngestionStatus(models.TextChoices):
        PENDING = "pending", _("Pending")
        PROCESSING = "processing", _("Processing")
        COMPLETED = "completed", _("Completed")
        FAILED = "failed", _("Failed")

    transaction_id = models.CharField(primary_key=True, max_length=100)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="transactions", db_column="account_id")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    date = models.DateTimeField()
    merchant_name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField()
    category = models.CharField(max_length=100, null=True, blank=True)  # Populated by enrichment
    batch_id = models.UUIDField()  # To track which ingestion request created this transaction
    ingestion_status = models.CharField(max_length=20, choices=IngestionStatus.choices, default=IngestionStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
