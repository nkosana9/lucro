# your_app/tasks.py
import logging
import random
import time

from celery import shared_task

from .enums import Category
from .models import Transaction

logger = logging.getLogger(__name__)


@shared_task
def categorise_transactions(batch_id: str):
    """
    A background task to categorise transactions in a given batch.

    :param batch_id: The batch ID of the transactions to categorise.
    """
    transactions = Transaction.objects.filter(batch_id=batch_id)

    for transaction in transactions:
        logger.info("Processing transaction: %s", transaction.transaction_id)
        transaction.ingestion_status = Transaction.IngestionStatus.PROCESSING
        transaction.save()

        # Simulate random processing latency
        time.sleep(random.uniform(0.5, 1))

        try:
            transaction.category = determine_transaction_category(transaction.description)
        except Exception as e:
            logger.error("Error categorising transaction %s: %s", transaction.transaction_id, e)
            transaction.ingestion_status = Transaction.IngestionStatus.FAILED
            transaction.save()
            continue

        transaction.ingestion_status = Transaction.IngestionStatus.COMPLETED
        transaction.save()
        logger.info("Categorised transaction %s as %s", transaction.transaction_id, transaction.category)


def determine_transaction_category(description: str) -> str:
    """
    Determine a transaction's category based on the given input.

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
    else:
        return Category.OTHER
