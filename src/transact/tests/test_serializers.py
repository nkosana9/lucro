from django.test import TestCase
from decimal import Decimal
from django.urls import reverse

from transact.serializers import CompositeCreationSerializer
from transact.models import Account, Transaction


class CompositeCreationSerializerTest(TestCase):
    def setUp(self):
        # Ensure clean state
        Account.objects.all().delete()
        Transaction.objects.all().delete()

    def test_create_accounts_and_transactions(self):
        """CompositeCreationSerializer.create should bulk create accounts and transactions and return batch info."""
        data = {
            "accounts": [
                {
                    "account_id": "acc_test_1",
                    "name": "Test 1",
                    "type": "checking",
                    "subtype": "personal",
                    "mask": "1111",
                },
                {
                    "account_id": "acc_test_2",
                    "name": "Test 2",
                    "type": "savings",
                    "subtype": "personal",
                    "mask": "2222",
                },
            ],
            "transactions": [
                {
                    "transaction_id": "t1",
                    "account_id": "acc_test_1",
                    "amount": Decimal("-12.34"),
                    "iso_currency_code": "USD",
                    "date": "2025-10-01T10:00:00Z",
                    "merchant_name": "Coffee",
                    "name": "Coffee purchase",
                },
                {
                    "transaction_id": "t2",
                    "account_id": "acc_test_2",
                    "amount": Decimal("100.00"),
                    "iso_currency_code": "USD",
                    "date": "2025-10-02T12:00:00Z",
                    "merchant_name": "Employer",
                    "name": "Salary",
                },
            ],
        }

        serializer = CompositeCreationSerializer(data=data)
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)

        result = serializer.save()

        # Response should include batch_id and total_transactions
        self.assertIn("batch_id", result)
        self.assertIn("total_transactions", result)
        self.assertEqual(result["total_transactions"], len(data["accounts"]) + len(data["transactions"]))

        # Accounts should be created
        self.assertTrue(Account.objects.filter(account_id="acc_test_1").exists())
        self.assertTrue(Account.objects.filter(account_id="acc_test_2").exists())

        # Transactions should be created and have the same batch_id
        tx1 = Transaction.objects.filter(transaction_id="t1").first()
        tx2 = Transaction.objects.filter(transaction_id="t2").first()
        self.assertIsNotNone(tx1)
        self.assertIsNotNone(tx2)

        # batch_id should be the same on both transactions
        self.assertEqual(str(tx1.batch_id), result["batch_id"])
        self.assertEqual(str(tx2.batch_id), result["batch_id"])
