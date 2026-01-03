from backend.database import SessionLocal
from backend.models import Category

def seed_categories(db=None):
    local_session = False
    if db is None:
        db = SessionLocal()
        local_session = True

    if db.query(Category).first():
        print("Categories already exist. Skipping category seed.")
        if local_session: db.close()
        return

    expense_categories = [
        'Food & Dining', 'Transportation', 'Shopping', 'Entertainment',
        'Bills & Utilities', 'Healthcare', 'Education', 'Travel',
        'Personal Care', 'Home & Rent', 'Insurance', 'Gifts & Donations', 'Other Expense'
    ]

    income_categories = [
        'Salary', 'Freelance', 'Investment', 'Business', 'Other Income'
    ]

    print("Adding expense categories...")
    for cat_name in expense_categories:
        db.add(Category(name=cat_name, type='expense'))

    print("Adding income categories...")
    for cat_name in income_categories:
        db.add(Category(name=cat_name, type='income'))

    db.commit()
    print(f"✅ Added {len(expense_categories) + len(income_categories)} categories")

    if local_session:
        db.close()

if __name__ == "__main__":
    seed_categories()
