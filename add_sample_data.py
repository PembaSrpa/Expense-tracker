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

    exp_categories = get_categories(db, type='expense')
    inc_categories = get_categories(db, type='income')

    if not exp_categories or not inc_categories:
        print("❌ No categories found. Please seed categories first!")
        return

    category_ids = [c.id for c in exp_categories]
    income_category_ids = [c.id for c in inc_categories]

    print("Adding 100 sample transactions...")
    for i in range(100):
        days_ago = random.randint(0, 180)
        create_transaction(
            db=db,
            date=date.today() - timedelta(days=days_ago),
            amount=round(random.uniform(15, 150), 2),
            category_id=random.choice(category_ids),
            description="Sample expense",
            transaction_type=TransactionType.expense
        )

    print("Adding income transactions...")
    for i in range(6):
        create_transaction(
            db=db,
            date=date.today() - timedelta(days=i*30),
            amount=3000.0,
            category_id=income_category_ids[0],
            description='Monthly salary',
            transaction_type=TransactionType.income
        )

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
    if local_session: db.close()

if __name__ == "__main__":
    seed_samples()
