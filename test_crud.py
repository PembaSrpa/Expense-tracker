from backend.database import SessionLocal
from backend.crud import create_transaction, get_transactions
from backend.models import TransactionType
from datetime import date

# Create a database session
db = SessionLocal()

# Test creating a transaction
transaction = create_transaction(
    db=db,
    date=date.today(),
    amount=50.0,
    category="food",
    description="Lunch",
    transaction_type=TransactionType.expense
)
print(f"✅ Created transaction: {transaction.id}")

# Test getting transactions
transactions = get_transactions(db)
print(f"✅ Total transactions: {len(transactions)}")

# Close the session
db.close()
