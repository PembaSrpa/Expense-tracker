from backend.database import SessionLocal
from backend.crud import create_transaction, get_categories
from backend.models import TransactionType
from datetime import date, timedelta
import random

def seed_ml_historical_data(db=None, months_back=12):
    local_session = False
    if db is None:
        db = SessionLocal()
        local_session = True

    all_categories = get_categories(db)
    income_cats = [c for c in all_categories if c.type == 'income']
    expense_cats = [c for c in all_categories if c.type == 'expense']

    if not expense_cats:
        print("❌ No expense categories found!")
        return

    current_date = (date.today() - timedelta(days=months_back * 30)).replace(day=1)
    month_count = 0

    try:
        while current_date <= date.today():
            trend_multiplier = 1 + (month_count * 0.02)
            for _ in range(random.randint(20, 30)):
                category = random.choice(expense_cats)
                create_transaction(
                    db=db,
                    date=current_date + timedelta(days=random.randint(0, 27)),
                    amount=round(random.uniform(20, 100) * trend_multiplier, 2),
                    category_id=category.id,
                    description=f"ML Test {category.name}",
                    transaction_type=TransactionType.expense
                )
            current_date = (current_date + timedelta(days=32)).replace(day=1)
            month_count += 1
        db.commit()
        print(f"✅ ML Data seeded for {month_count} months.")
    finally:
        if local_session: db.close()

if __name__ == "__main__":
    seed_ml_historical_data()
