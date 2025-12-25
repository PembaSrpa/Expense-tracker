from backend.database import SessionLocal
from backend.crud import create_transaction, create_budget, get_category_by_name
from backend.models import TransactionType
from datetime import date

db = SessionLocal()

print("Creating test data for budget alerts...\n")

# Get a category
food_category = get_category_by_name(db, "Food & Dining")
if not food_category:
    print("❌ Food & Dining category not found!")
    db.close()
    exit()

print(f"✅ Found category: {food_category.name} (ID: {food_category.id})")

# Create a budget for this month
budget = create_budget(
    db=db,
    category_id=food_category.id,
    monthly_limit=500.0,
    start_date=date.today()
)
print(f"✅ Created budget: ${budget.monthly_limit} for {food_category.name}")

# Add transactions this month that exceed 75% of budget
transactions = [
    {"amount": 200.0, "desc": "Groceries"},
    {"amount": 150.0, "desc": "Restaurant"},
    {"amount": 100.0, "desc": "Fast food"},
]

total = 0
for trans in transactions:
    create_transaction(
        db=db,
        date=date.today(),
        amount=trans["amount"],
        category_id=food_category.id,
        description=trans["desc"],
        transaction_type=TransactionType.expense
    )
    total += trans["amount"]
    print(f"✅ Added transaction: ${trans['amount']} - {trans['desc']}")

percentage = (total / budget.monthly_limit) * 100
print(f"\n📊 Total spent: ${total} / ${budget.monthly_limit} ({percentage:.1f}%)")

if percentage >= 75:
    print(f"✅ Should trigger alert! (>75%)")
else:
    print(f"⚠️  Won't trigger alert yet (<75%)")

print(f"\n🧪 Now test: GET /analytics/budget-alerts")

db.close()
