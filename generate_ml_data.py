from backend.database import SessionLocal
from backend.crud import create_transaction, get_categories
from backend.models import TransactionType
from datetime import date, timedelta
import random

db = SessionLocal()

print("Generating historical data for ML predictions...\n")

# Get categories
expense_categories = get_categories(db, type='expense')
income_categories = get_categories(db, type='income')

if not expense_categories:
    print("❌ No categories found! Run add_default_categories.py first")
    db.close()
    exit()

# Generate data for past 18 months
today = date.today()
start_date = today - timedelta(days=18 * 30)

print("Creating transactions for past 18 months...")

# Track month for adding trend
month_count = 0

# Generate transactions month by month
current_date = start_date
while current_date <= today:
    month_start = date(current_date.year, current_date.month, 1)

    # Next month start
    if current_date.month == 12:
        next_month = date(current_date.year + 1, 1, 1)
    else:
        next_month = date(current_date.year, current_date.month + 1, 1)

    month_end = next_month - timedelta(days=1)

    # Add slight upward trend (spending increases 2% per month)
    trend_multiplier = 1 + (month_count * 0.02)

    # Create 20-40 transactions per month
    num_transactions = random.randint(20, 40)

    for _ in range(num_transactions):
        # Random date in month
        day_offset = random.randint(0, (month_end - month_start).days)
        trans_date = month_start + timedelta(days=day_offset)

        # Random category
        category = random.choice(expense_categories)

        # Base amount varies by category
        if 'Food' in category.name:
            base_amount = random.uniform(10, 80)
        elif 'Transport' in category.name:
            base_amount = random.uniform(20, 100)
        elif 'Bills' in category.name or 'Rent' in category.name:
            base_amount = random.uniform(50, 500)
        else:
            base_amount = random.uniform(15, 120)

        # Apply trend
        amount = base_amount * trend_multiplier

        # Add some randomness
        amount *= random.uniform(0.8, 1.2)

        create_transaction(
            db=db,
            date=trans_date,
            amount=round(amount, 2),
            category_id=category.id,
            description=f"{category.name} expense",
            transaction_type=TransactionType.expense
        )

    # Add monthly income
    if income_categories:
        salary_date = month_start + timedelta(days=random.randint(1, 5))
        create_transaction(
            db=db,
            date=salary_date,
            amount=random.uniform(2800, 3200),
            category_id=income_categories[0].id,
            description="Monthly salary",
            transaction_type=TransactionType.income
        )

    print(f"✅ Generated {num_transactions} transactions for {month_start.strftime('%B %Y')}")

    current_date = next_month
    month_count += 1

print(f"\n🎉 Created transactions for 18 months!")
print("Now you can test ML predictions with realistic data.")

db.close()
