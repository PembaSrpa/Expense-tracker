from backend.database import SessionLocal
from backend.crud import create_transaction, create_budget, get_categories
from backend.models import TransactionType
from datetime import date, timedelta
import random

db = SessionLocal()

# Get all categories
categories = get_categories(db, type='expense')
category_ids = [c.id for c in categories]
category_dict = {c.name: c.id for c in categories}

# Get income categories
income_categories = get_categories(db, type='income')
income_category_ids = [c.id for c in income_categories]

print("Adding sample transactions...")
for i in range(100):
    days_ago = random.randint(0, 180)
    transaction_date = date.today() - timedelta(days=days_ago)

    # Random category
    category_id = random.choice(category_ids)
    amount = random.uniform(15, 150)

    create_transaction(
        db=db,
        date=transaction_date,
        amount=round(amount, 2),
        category_id=category_id,
        description=f"Sample expense",
        transaction_type=TransactionType.expense
    )

print("✅ Added 100 sample transactions")

# Add income
print("Adding income transactions...")
for i in range(6):
    income_date = date.today() - timedelta(days=i*30)
    create_transaction(
        db=db,
        date=income_date,
        amount=3000.0,
        category_id=income_category_ids[0],
        description='Monthly salary',
        transaction_type=TransactionType.income
    )

print("✅ Added 6 income transactions")

# Add budgets
print("Adding budgets...")
for cat in categories[:6]:  # First 6 expense categories
    create_budget(
        db=db,
        category_id=cat.id,  # CHANGED
        monthly_limit=random.uniform(200, 500),
        start_date=date.today() - timedelta(days=180)
    )

print("✅ Added budgets")
print("\n🎉 Sample data added successfully!")

db.close()
