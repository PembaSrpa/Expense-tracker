from backend.database import SessionLocal
from backend.models import Category

def seed_categories(db=None):
    # Use provided session or create a new one
    local_session = False
    if db is None:
        db = SessionLocal()
        local_session = True

    # Check if categories already exist to prevent duplicates
    if db.query(Category).first():
        print("Categories already exist. Skipping category seed.")
        return

    # Default expense categories
    expense_categories = [
        'Food & Dining', 'Transportation', 'Shopping', 'Entertainment',
        'Bills & Utilities', 'Healthcare', 'Education', 'Travel',
        'Personal Care', 'Home & Rent', 'Insurance', 'Gifts & Donations', 'Other Expense'
    ]

    # Default income categories
    income_categories = [
        'Salary', 'Freelance', 'Investment', 'Business', 'Other Income'
    ]

    print("Adding expense categories...")
    for cat_name in expense_categories:
        category = Category(name=cat_name, type='expense')
        db.add(category)

    print("Adding income categories...")
    for cat_name in income_categories:
        category = Category(name=cat_name, type='income')
        db.add(category)

    db.commit()
    print(f"✅ Added {len(expense_categories) + len(income_categories)} categories")

    if local_session:
        db.close()
