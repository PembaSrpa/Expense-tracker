from backend.database import SessionLocal
from backend.crud import create_transaction, create_budget
from backend.models import TransactionType
from datetime import date, timedelta
import random

db = SessionLocal()

# Sample categories
categories = ['food', 'transport', 'entertainment', 'utilities', 'shopping', 'health']

# Add transactions for the last 6 months
today = date.today()

print("Adding sample transactions...")
for i in range(100):
    # Random date in last 6 months
    days_ago = random.randint(0, 180)
    transaction_date = today - timedelta(days=days_ago)

    # Random category and amount
    category = random.choice(categories)

    # Different amount ranges for different categories
    if category == 'food':
        amount = random.uniform(10, 100)
    elif category == 'transport':
        amount = random.uniform(20, 150)
    elif category == 'utilities':
        amount = random.uniform(50, 200)
    else:
        amount = random.uniform(15, 120)

    create_transaction(
        db=db,
        date=transaction_date,
        amount=round(amount, 2),
        category=category,
        description=f"Sample {category} expense",
        transaction_type=TransactionType.expense
    )

print("✅ Added 100 sample transactions")

# Add some income transactions
print("Adding income transactions...")
for i in range(6):
    income_date = today - timedelta(days=i*30)
    create_transaction(
        db=db,
        date=income_date,
        amount=3000.0,
        category='salary',
        description='Monthly salary',
        transaction_type=TransactionType.income
    )

print("✅ Added 6 income transactions")

# Add budgets
print("Adding budgets...")
for category in categories:
    create_budget(
        db=db,
        category=category,
        monthly_limit=random.uniform(200, 500),
        start_date=today - timedelta(days=180)
    )

print("✅ Added budgets for all categories")
print("\n🎉 Sample data added successfully!")

db.close()
