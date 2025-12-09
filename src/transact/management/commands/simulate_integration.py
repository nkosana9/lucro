import json
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from django.core.management.base import BaseCommand

tz = ZoneInfo("UTC")

MAX_ACCOUNTS_PER_BATCH = 3


class MyIngestionRequest:
    """A simple encapsulating the process of simulating ingestion requests."""

    # Assuming one account type just for simplicity
    ACCOUNT = {
        "name": "Simulated Account",
        "type": "checking",
        "subtype": "simulated",
        "mask": "0000",
    }

    MERCHANTS = [
        ("Amazon", "Amazon Marketplace"),
        ("AWS", "Amazon Web Service"),
        ("Azure", "Microsoft Azure"),
        ("Lyft", "Lyft Rides"),
        ("Paypal", "Paypal"),
        ("Stripe", "Stripe Payments"),
        ("Uber", "Uber"),
    ]

    def __init__(self, num_transactions: int):
        self.account_ids = [self._get_random_account_id() for _ in range(MAX_ACCOUNTS_PER_BATCH)]
        self.num_transactions = num_transactions

    def _get_random_transaction_id(self) -> str:
        """Generate a random transaction ID of the form 'tx_sim_XXX' where XXX is a random 3-digit number."""
        return "tx_sim_" + f"{random.uniform(100, 999):.0f}"

    def _get_random_account_id(self) -> str:
        """Generate a random account ID of the form 'acc_sim_XXXX' where XXXX is a random 4-digit number."""
        return "acc_sim_" + f"{random.uniform(1000, 9999):.0f}"

    def get_random_request_id(self) -> str:
        """Generate a random request ID of the form 'req_sim_XXXYYY' where X is a random digit and Y is a random letter"""
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        digits = "".join(str(random.randint(0, 9)) for _ in range(3))
        chars = "".join(random.choice(letters) for _ in range(3))
        return f"req_sim_{chars}{digits}"

    def _build_account(self, account_id: str) -> dict:
        """Build a single account payload with the given account ID."""
        account = self.ACCOUNT.copy()
        account["account_id"] = account_id
        return account

    def _build_transaction(self) -> dict:
        """Build a single transaction payload for a randomly-chosen account."""
        account_id = random.choice(self.account_ids)
        transaction_id = self._get_random_transaction_id()
        merchant, description = random.choice(self.MERCHANTS)

        # Assuming transaction amounts would generally be a few larger positives (income) followed by smaller expenses
        if random.random() < 0.15:
            amount = round(random.uniform(100.0, 3000.0), 2)  # income
        else:
            amount = round(-random.uniform(3.0, 250.0), 2)  # expense

        # Random date within last 30 days
        days_ago = random.randint(0, 29)
        when = datetime.now(tz) - timedelta(days=days_ago)

        return {
            "transaction_id": transaction_id,
            "account_id": account_id,
            "amount": str(amount),
            "iso_currency_code": "USD",
            "date": when.isoformat(),
            "authorized_date": when.date().isoformat(),
            "name": description,
            "merchant_name": merchant,
            "payment_channel": "online",
            "pending": False,
        }

    def build_payload(self):
        accounts = [self._build_account(account_id) for account_id in self.account_ids]
        transactions = [self._build_transaction() for _ in range(self.num_transactions)]

        return {
            "accounts": accounts,
            "transactions": transactions,
            "total_transactions": self.num_transactions + len(self.account_ids),
            "request_id": f"req_{random.randint(100000, 999999)}",
        }


class Command(BaseCommand):
    help = "Simulate an integration by generating transactions and posting them to the ingestion endpoint."

    def add_arguments(self, parser):
        parser.add_argument("--server", default="http://localhost:8000", help="Base server URL")
        parser.add_argument("--count", type=int, default=10, help="Number of transactions to generate in the batch")
        parser.add_argument("--token", required=True, help="DRF Token to use for Authorization header")

    def _post_json(self, url, data: str, headers=None):
        resp = requests.post(url, data=data, headers=headers or {}, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def handle(self, *args, **options):
        server = options["server"].rstrip("/")
        count = options["count"]
        token = options["token"]

        headers = {"Content-Type": "application/json", "Authorization": f"Token {token}"}
        ingestion_url = f"{server}/api/integrations/transactions/"

        my_request = MyIngestionRequest(num_transactions=count)

        # Generate transactions with progress
        self.stdout.write(f"Generating {count} transactions for the account IDs {my_request.account_ids}...")
        payload = my_request.build_payload()
        formatted_payload = json.dumps(payload)

        self.stdout.write(self.style.SUCCESS("Transaction generation complete."))
        self.stdout.write("payload preview:")
        self.stdout.write(formatted_payload)
        self.stdout.write(f"Posting batch to {ingestion_url}...")

        try:
            resp = self._post_json(ingestion_url, formatted_payload, headers=headers)
        except Exception as e:
            self.stderr.write(f"Failed to post batch: {e}")
            return

        # The API returns a batch_id and total_transactions (per CompositeCreationSerializer implementation)
        batch_id = resp.get("batch_id") or resp.get("id") or "<unknown>"
        total = resp.get("total_transactions")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Batch posted successfully: batch_id={batch_id}, total={total}"))
