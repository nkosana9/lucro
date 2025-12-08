from django.db import models
from django.utils.translation import gettext_lazy as _


class Account(models.Model):
    account_id = models.CharField(primary_key=True, max_length=100)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50)
    subtype = models.CharField(max_length=50, null=True, blank=True)
    mask = models.CharField(max_length=10, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Transaction(models.Model):

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
