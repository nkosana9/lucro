# your_app/tasks.py
import logging
import random
import time

from celery import shared_task
from celery.utils.log import get_task_logger

from .enums import Category
from .models import Transaction

logger = get_task_logger(__name__)


@shared_task
def categorise_transactions(batch_id: str):
    """
    A background task to categorise transactions in a given batch.
    Only processes transactions with 'pending' status.

    :param batch_id: The batch ID of the transactions to categorise.
    """
    transactions = Transaction.objects.filter(batch_id=batch_id)

    for transaction in transactions:
        if transaction.ingestion_status == Transaction.IngestionStatus.PENDING:
            logger.info("Processing transaction: %s", transaction.transaction_id)
            transaction.ingestion_status = Transaction.IngestionStatus.PROCESSING
            transaction.save()

            time.sleep(random.uniform(0.5, 1))  # Simulate random processing latency

            try:
                transaction.category = determine_transaction_category(transaction.description)
            except Exception as e:
                logger.exception("Error categorising transaction %s: %s", transaction.transaction_id, e)
                transaction.ingestion_status = Transaction.IngestionStatus.FAILED
                transaction.save()
                continue

            transaction.ingestion_status = Transaction.IngestionStatus.COMPLETED
            transaction.save()
            logger.info("Categorised transaction %s as %s", transaction.transaction_id, transaction.category)
        else:
            logger.warning(
                "Skipping transaction %s with status %s", transaction.transaction_id, transaction.ingestion_status
            )


def determine_transaction_category(description: str) -> str:
    """
    Determine a transaction's category based on the given input.
    Can be swapped out for a more complex ML model or external service.

    :param description: The transaction description.
    :return: The determined category.
    """
    description_lower = description.lower()
    if "amazon" in description_lower:
        return Category.SHOPPING
    elif "stripe" in description_lower or "paypal" in description_lower:
        return Category.INCOME
    elif "uber" in description_lower or "lyft" in description_lower:
        return Category.TRANSPORT
    elif "aws" in description_lower or "azure" in description_lower:
        return Category.SOFTWARE

    raise ValueError("Unable to determine category from description")
