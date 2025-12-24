from backend.database import SessionLocal
from backend.crud import create_transaction, create_budget, get_categories
from backend.models import TransactionType
from datetime import date, timedelta
import random

def seed_samples(db=None):
    local_session = False
    if db is None:
        db = SessionLocal()
        local_session = True

    # 1. Get categories (must run after categories are seeded)
    exp_categories = get_categories(db, type='expense')
    inc_categories = get_categories(db, type='income')

    if not exp_categories or not inc_categories:
        print("❌ No categories found. Please seed categories first!")
        return

    category_ids = [c.id for c in exp_categories]
    income_category_ids = [c.id for c in inc_categories]

    # 2. Add sample transactions
    print("Adding 100 sample transactions...")
    for i in range(100):
        days_ago = random.randint(0, 180)
        transaction_date = date.today() - timedelta(days=days_ago)
        category_id = random.choice(category_ids)
        amount = random.uniform(15, 150)

        create_transaction(
            db=db,
            date=transaction_date,
            amount=round(amount, 2),
            category_id=category_id,
            description="Sample expense",
            transaction_type=TransactionType.expense
        )

    # 3. Add income
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

    # 4. Add budgets
    print("Adding budgets...")
    for cat in exp_categories[:6]:
        create_budget(
            db=db,
            category_id=cat.id,
            monthly_limit=round(random.uniform(200, 500), 2),
            start_date=date.today() - timedelta(days=180)
        )

    db.commit()
    print("✅ Sample data added successfully!")

    if local_session:
        db.close()
