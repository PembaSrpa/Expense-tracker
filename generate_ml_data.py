from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.crud import create_transaction, get_categories
from backend.models import TransactionType
from datetime import date, timedelta
import random

def seed_ml_historical_data(db=None, months_back=12):
    """
    Generates realistic historical data with a slight upward trend
    to test Scikit-learn prediction models.
    """
    # Pattern fix: Handle session same as seed_samples
    local_session = False
    if db is None:
        db = SessionLocal()
        local_session = True

    print(f"Generating historical data for {months_back} months...")

    # 1. Get categories
    all_categories = get_categories(db)
    income_categories = [c for c in all_categories if "Salary" in c.name or "Income" in c.name]
    actual_expenses = [c for c in all_categories if c not in income_categories]

    if not actual_expenses:
        print("❌ No expense categories found! Please seed categories first.")
        if local_session: db.close()
        return

    # 2. Setup dates
    today = date.today()
    start_date = today - timedelta(days=months_back * 30)
    current_date = start_date
    month_count = 0

    try:
        # 3. Generate data month by month
        while current_date <= today:
            month_start = date(current_date.year, current_date.month, 1)

            # Calculate next month
            if current_date.month == 12:
                next_month = date(current_date.year + 1, 1, 1)
            else:
                next_month = date(current_date.year, current_date.month + 1, 1)

            month_end = next_month - timedelta(days=1)

            # Trend logic: spending increases 2% per month
            trend_multiplier = 1 + (month_count * 0.02)
            num_transactions = random.randint(20, 40)

            for _ in range(num_transactions):
                day_offset = random.randint(0, (month_end - month_start).days)
                trans_date = month_start + timedelta(days=day_offset)

                category = random.choice(actual_expenses)

                if 'Food' in category.name:
                    base_amount = random.uniform(10, 80)
                elif 'Transport' in category.name:
                    base_amount = random.uniform(20, 100)
                elif 'Bills' in category.name or 'Rent' in category.name:
                    base_amount = random.uniform(50, 500)
                else:
                    base_amount = random.uniform(15, 120)

                final_amount = round(base_amount * trend_multiplier * random.uniform(0.8, 1.2), 2)

                create_transaction(
                    db=db,
                    date=trans_date,
                    amount=final_amount,
                    category_id=category.id,
                    description=f"{category.name} expense",
                    transaction_type=TransactionType.expense
                )

            # 4. Add monthly income
            if income_categories:
                salary_date = month_start + timedelta(days=random.randint(1, 5))
                create_transaction(
                    db=db,
                    date=salary_date,
                    amount=round(random.uniform(2800, 3200), 2),
                    category_id=income_categories[0].id,
                    description="Monthly salary",
                    transaction_type=TransactionType.income
                )

            print(f"✅ Generated data for {month_start.strftime('%B %Y')}")
            current_date = next_month
            month_count += 1

        db.commit()
        print(f"\n🎉 Successfully created transactions for {month_count} months!")

    except Exception as e:
        db.rollback()
        print(f"⚠️ Error during ML data generation: {e}")
    finally:
        # Crucial: Clean up session if it was created locally
        if local_session:
            db.close()

if __name__ == "__main__":
    seed_ml_historical_data()
