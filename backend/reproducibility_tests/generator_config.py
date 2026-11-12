import random
from datetime import date, timedelta
from decimal import Decimal

SEED = 20261022
USER_COUNT = 2
TRANSACTIONS_PER_USER = 50
BATCH_SIZE = 100
TOTAL_TRANSACTIONS = USER_COUNT * TRANSACTIONS_PER_USER

random.seed(SEED)

print("Seed:", SEED)
print("Users:", USER_COUNT)
print("Transactions:", TOTAL_TRANSACTIONS)
