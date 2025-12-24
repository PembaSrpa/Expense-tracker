# test_crud.py
from backend.database import SessionLocal, engine
from backend import crud, models
from backend.models import TransactionType
from datetime import date

# Ensure tables are created (optional if already created)
models.Base.metadata.create_all(bind=engine)

def run_test():
    db = SessionLocal()
    try:
        print("--- Testing Category Operations ---")
        # 1. Create a category first (to avoid Foreign Key errors)
        existing_cat = crud.get_category_by_name(db, "Food")
        if not existing_cat:
            category = crud.create_category(db, name="Food", type="expense")
            print(f"✅ Created category: {category.name} (ID: {category.id})")
        else:
            category = existing_cat
            print(f"ℹ️ Category '{category.name}' already exists (ID: {category.id})")

        print("\n--- Testing Budget Operations ---")
        # 2. Create or Update a budget for that category
        budget = crud.get_budget_by_category_id(db, category.id)
        if not budget:
            budget = crud.create_budget(db, category_id=category.id, monthly_limit=500.0, start_date=date.today())
            print(f"✅ Created budget: ${budget.monthly_limit}")
        else:
            print(f"ℹ️ Budget exists: ${budget.monthly_limit}")

        print("\n--- Testing Transaction Operations ---")
        # 3. Create a transaction using the INTEGER ID
        transaction = crud.create_transaction(
            db=db,
            date=date.today(),
            amount=50.0,
            category_id=category.id,  # Passing the integer ID
            description="Lunch at Cafe",
            transaction_type=TransactionType.expense
        )
        print(f"✅ Created transaction ID: {transaction.id}")

        # 4. Get transactions
        transactions = crud.get_transactions(db)
        print(f"✅ Total transactions in DB: {len(transactions)}")

        print("\n--- Testing Analytics ---")
        # 5. Test the join logic in analytics
        spending = crud.get_spending_by_category(db)
        for s in spending:
            print(f"📊 Category: {s.category} | Total Spent: ${s.total}")

    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        db.close()
        print("\n--- Test Suite Complete ---")

if __name__ == "__main__":
    run_test()
