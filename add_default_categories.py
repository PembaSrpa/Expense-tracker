from backend.database import SessionLocal
from backend.models import Category

db = SessionLocal()

# Default expense categories
expense_categories = [
    'Food & Dining',
    'Transportation',
    'Shopping',
    'Entertainment',
    'Bills & Utilities',
    'Healthcare',
    'Education',
    'Travel',
    'Personal Care',
    'Home & Rent',
    'Insurance',
    'Gifts & Donations',
    'Other Expense'
]

# Default income categories
income_categories = [
    'Salary',
    'Freelance',
    'Investment',
    'Business',
    'Other Income'
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
print(f"✅ Added {len(expense_categories)} expense categories")
print(f"✅ Added {len(income_categories)} income categories")

# Show all categories
categories = db.query(Category).all()
print("\nCategories in database:")
for cat in categories:
    print(f"  ID: {cat.id}, Name: {cat.name}, Type: {cat.type}")

db.close()
