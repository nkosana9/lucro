import uuid
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import TestCase

from transact.enums import Category
from transact.models import Account, Transaction
from transact.task import categorise_transactions

tz = ZoneInfo("UTC")


class CategoriseTransactionsTaskTest(TestCase):
    def setUp(self):
        Account.objects.all().delete()
        Transaction.objects.all().delete()

        self.account = Account.objects.create(
            account_id="acc_task_test",
            name="Task Test",
            type="checking",
        )

    @patch("transact.task.time.sleep", lambda *_: None)
    def test_categorise_transactions_success_and_skip(self):
        batch_id = uuid.uuid4()

        # Pending transactions that should be categorised
        t1 = Transaction.objects.create(
            transaction_id="task_t1",
            account=self.account,
            amount=Decimal("-34.50"),
            currency="USD",
            date=datetime.now(tz),
            merchant_name="Amazon",
            description="Amazon order #123",
            category=None,
            batch_id=batch_id,
            ingestion_status=Transaction.IngestionStatus.PENDING,
        )

        t2 = Transaction.objects.create(
            transaction_id="task_t2",
            account=self.account,
            amount=Decimal("-12.00"),
            currency="USD",
            date=datetime.now(tz),
            merchant_name="Uber",
            description="Uber ride",
            category=None,
            batch_id=batch_id,
            ingestion_status=Transaction.IngestionStatus.PENDING,
        )

        # Transaction from different batch should not be processed
        other = Transaction.objects.create(
            transaction_id="task_other",
            account=self.account,
            amount=Decimal("-5.00"),
            currency="USD",
            date=datetime.now(tz),
            merchant_name="Cafe",
            description="Coffee",
            category=None,
            batch_id=uuid.uuid4(),
            ingestion_status=Transaction.IngestionStatus.PENDING,
        )

        # Already completed transaction should be skipped
        completed = Transaction.objects.create(
            transaction_id="task_done",
            account=self.account,
            amount=Decimal("-20.00"),
            currency="USD",
            date=datetime.now(tz),
            merchant_name="Store",
            description="Store",
            category="Shopping",
            batch_id=batch_id,
            ingestion_status=Transaction.IngestionStatus.COMPLETED,
        )

        # Run the task synchronously
        categorise_transactions(str(batch_id))

        # Refresh from DB
        t1.refresh_from_db()
        t2.refresh_from_db()
        other.refresh_from_db()
        completed.refresh_from_db()

        # Check categories assigned
        self.assertEqual(t1.category, Category.SHOPPING)
        self.assertEqual(t2.category, Category.TRANSPORT)

        # Other batch should remain unprocessed (still pending)
        self.assertEqual(other.ingestion_status, Transaction.IngestionStatus.PENDING)

        # Completed remained completed and category unchanged
        self.assertEqual(completed.ingestion_status, Transaction.IngestionStatus.COMPLETED)
        self.assertEqual(completed.category, "Shopping")

    @patch("transact.task.time.sleep", lambda *_: None)
    def test_categorise_transactions_handles_bad_description(self):
        batch_id = uuid.uuid4()

        # description is None - determine_transaction_category will raise
        bad = Transaction.objects.create(
            transaction_id="task_bad",
            account=self.account,
            amount=Decimal("-7.00"),
            currency="USD",
            date=datetime.now(tz),
            merchant_name=None,
            description="",
            batch_id=batch_id,
            ingestion_status=Transaction.IngestionStatus.PENDING,
        )

        # Run task
        categorise_transactions(str(batch_id))

        bad.refresh_from_db()

        # Because the task's exception handling sets FAILED then (unfortunately)
        # sets COMPLETED afterwards, final status is COMPLETED in current code.
        self.assertEqual(bad.ingestion_status, Transaction.IngestionStatus.FAILED)

        # Category should remain None because categorisation failed
        self.assertIsNone(bad.category)
