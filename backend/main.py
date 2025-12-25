from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import crud
from backend.models import TransactionType
from pydantic import BaseModel
import datetime
from datetime import date
from typing import Optional, List, Union
from backend import analytics
from backend import visualizations
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from backend import exports
from fastapi.responses import StreamingResponse
from backend import ml_predictions
import io

# Pydantic models for request/response validation

class TransactionCreate(BaseModel):
    date: date
    amount: float
    category_name: str
    description: Optional[str] = None
    transaction_type: TransactionType

class TransactionUpdate(BaseModel):
    # Using Union[datetime.date, None] is the safest way to avoid the "Should be None" error
    date: Union[datetime.date, None] = None
    amount: Union[float, None] = None
    category_name: Union[str, None] = None
    description: Union[str, None] = None
    transaction_type: Union[TransactionType, None] = None

class TransactionResponse(BaseModel):
    id: int
    date: date
    amount: float
    category_name: str
    description: Optional[str]
    transaction_type: TransactionType

    class Config:
        from_attributes = True

class BudgetCreate(BaseModel):
    category_name: str
    monthly_limit: float
    start_date: date

class BudgetResponse(BaseModel):
    id: int
    category_name: str
    monthly_limit: float
    start_date: date

    class Config:
        from_attributes = True

class CategoryCreate(BaseModel):
    name: str
    type: str  # 'income' or 'expense'

class CategoryResponse(BaseModel):
    id: int
    name: str
    type: str

    class Config:
        from_attributes = True

# Create FastAPI app
app = FastAPI(
    title="Expense Tracker API",
    description="API for tracking expenses and managing budgets",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (for development)
#     allow_origins=[
#     "http://localhost:3000",  # Your frontend
#     "https://yourdomain.com", # (for production)
# ]
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)
# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Hao"}

# ============= TRANSACTION ENDPOINTS =============

@app.post("/transactions", response_model=TransactionResponse)
def create_transaction(transaction: TransactionCreate, db: Session = Depends(get_db)):
    """Create a new transaction"""

    # Find category by name
    category = crud.get_category_by_name(db, transaction.category_name)
    if not category:
        # Show helpful error with available categories
        available = [c.name for c in crud.get_categories(db)]
        raise HTTPException(
            status_code=404,
            detail=f"Category '{transaction.category_name}' not found. Available categories: {', '.join(available)}"
        )

    # Create transaction with category ID (internal)
    db_transaction = crud.create_transaction(
        db=db,
        date=transaction.date,
        amount=transaction.amount,
        category_id=category.id,
        description=transaction.description,
        transaction_type=transaction.transaction_type
    )

    return {
        "id": db_transaction.id,
        "date": db_transaction.date,
        "amount": db_transaction.amount,
        "category_name": db_transaction.category_rel.name,
        "description": db_transaction.description,
        "transaction_type": db_transaction.transaction_type
    }

@app.get("/transactions", response_model=List[TransactionResponse])
def get_transactions(
    skip: int = 0,
    limit: int = 100,
    category_name: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    transaction_type: Optional[TransactionType] = None,
    db: Session = Depends(get_db)
):
    """Get all transactions with optional filters"""

    # Convert category name to ID if provided
    category_id = None
    if category_name:
        category = crud.get_category_by_name(db, category_name)
        if category:
            category_id = category.id

    transactions = crud.get_transactions(
        db=db,
        skip=skip,
        limit=limit,
        category_id=category_id,
        start_date=start_date,
        end_date=end_date,
        transaction_type=transaction_type
    )

    # Return with category names
    return [
        {
            "id": t.id,
            "date": t.date,
            "amount": t.amount,
            "category_name": t.category_rel.name,
            "description": t.description,
            "transaction_type": t.transaction_type
        }
        for t in transactions
    ]

@app.get("/transactions/{transaction_id}", response_model=TransactionResponse)
def get_transaction(transaction_id: int, db: Session = Depends(get_db)):
    """Get a specific transaction by ID"""
    transaction = crud.get_transaction_by_id(db, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction

@app.put("/transactions/{transaction_id}", response_model=TransactionResponse)
def update_transaction(transaction_id: int, transaction: TransactionUpdate, db: Session = Depends(get_db)):
    # 1. Look up the category ID first
    update_data = transaction.dict(exclude_unset=True)

    if "category_name" in update_data:
        category = crud.get_category_by_name(db, name=update_data["category_name"])
        if not category:
            raise HTTPException(status_code=400, detail="Category not found")
        update_data["category_id"] = category.id
        del update_data["category_name"]

    # 2. Update using the ID
    db_transaction = crud.update_transaction(
        db,
        transaction_id=transaction_id,
        **update_data
    )

    if not db_transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return db_transaction

@app.delete("/transactions/{transaction_id}")
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    """Delete a transaction"""
    success = crud.delete_transaction(db, transaction_id)
    if not success:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"message": "Transaction deleted successfully"}

# ============= CATEGORY ENDPOINTS =============

@app.post("/categories", response_model=CategoryResponse)
def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    """Create a new category"""
    return crud.create_category(db, name=category.name, type=category.type)

@app.get("/categories", response_model=List[CategoryResponse])
def get_categories(type: Optional[str] = None, db: Session = Depends(get_db)):
    """Get all categories, optionally filtered by type"""
    return crud.get_categories(db, type=type)

# ============= BUDGET ENDPOINTS =============

@app.post("/budgets", response_model=BudgetResponse)
def create_budget(budget: BudgetCreate, db: Session = Depends(get_db)):
    """Create a new budget"""

    # 1. Find category by name
    category = crud.get_category_by_name(db, budget.category_name)
    if not category:
        available = [c.name for c in crud.get_categories(db, type='expense')]
        raise HTTPException(
            status_code=404,
            detail=f"Category '{budget.category_name}' not found. Available: {', '.join(available)}"
        )

    # 2. Check if a budget already exists using the ID (Fixing the AttributeError here)
    existing_budget = crud.get_budget_by_category_id(db, category.id)
    if existing_budget:
        raise HTTPException(
            status_code=400,
            detail=f"A budget for '{budget.category_name}' already exists. Please update the existing one."
        )

    # 3. Create the budget
    db_budget = crud.create_budget(
        db=db,
        category_id=category.id,
        monthly_limit=budget.monthly_limit,
        start_date=budget.start_date
    )

    return {
        "id": db_budget.id,
        "category_name": db_budget.category_rel.name,
        "monthly_limit": db_budget.monthly_limit,
        "start_date": db_budget.start_date
    }

@app.get("/budgets", response_model=List[BudgetResponse])
def get_budgets(db: Session = Depends(get_db)):
    """Get all budgets with category name mapping"""
    budgets = crud.get_budgets(db)

    # Map SQLAlchemy objects to dictionaries with category_name
    return [
        {
            "id": b.id,
            "category_name": b.category_rel.name if b.category_rel else "Unknown",
            "monthly_limit": b.monthly_limit,
            "start_date": b.start_date
        }
        for b in budgets
    ]

@app.get("/budgets/{category}", response_model=BudgetResponse)
def get_budget_by_category_name(category: str, db: Session = Depends(get_db)):
    """Get budget for a specific category name"""

    # 1. First, find the category object using the string name
    category_obj = crud.get_category_by_name(db, category)
    if not category_obj:
        raise HTTPException(status_code=404, detail=f"Category '{category}' not found")

    # 2. Now use the ID from that object to call your CRUD function
    budget = crud.get_budget_by_category_id(db, category_id=category_obj.id)

    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found for this category")

    return {
        "id": budget.id,
        "category_name": budget.category_rel.name,
        "monthly_limit": budget.monthly_limit,
        "start_date": budget.start_date
    }

@app.delete("/budgets/{budget_id}")
def delete_budget(budget_id: int, db: Session = Depends(get_db)):
    """Delete a budget"""
    success = crud.delete_budget(db, budget_id)
    if not success:
        raise HTTPException(status_code=404, detail="Budget not found")
    return {"message": "Budget deleted successfully"}

# ============= ANALYTICS ENDPOINTS =============

@app.get("/analytics/spending-by-category")
def get_spending_by_category(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    return analytics.get_top_spending_categories(db, limit=100, start_date=start_date, end_date=end_date)

@app.get("/analytics/income-expense")
def get_income_expense(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    df = analytics.transactions_to_dataframe(db, start_date, end_date)
    if df.empty:
        return {"income": 0, "expense": 0}

    totals = df.groupby('type')['amount'].sum().to_dict()
    return {
        "income": float(totals.get('income', 0)),
        "expense": float(totals.get('expense', 0))
    }

@app.get("/analytics/budget-vs-actual/{category_id}")
def get_budget_comparison(
    category_id: int,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):
    """Compare budget to actual spending"""
    return crud.get_budget_vs_actual(db, category_id, start_date, end_date)

@app.get("/analytics/monthly-trend")
def get_monthly_trend(months: int = 6, db: Session = Depends(get_db)):
    """Get monthly spending trend"""
    return analytics.get_monthly_spending_trend(db, months)

@app.get("/analytics/category-trend/{category}")
def get_category_trend_endpoint(category: str, months: int = 6, db: Session = Depends(get_db)):
    """Get spending trend for a specific category"""
    return analytics.get_category_trend(db, category, months)

@app.get("/analytics/spending-patterns")
def get_patterns(db: Session = Depends(get_db)):
    """Get spending patterns analysis"""
    return analytics.get_spending_patterns(db)

@app.get("/analytics/top-categories")
def get_top_categories(limit: int = 5, db: Session = Depends(get_db)):
    """Get top spending categories"""
    return analytics.get_top_spending_categories(db, limit)

@app.get("/analytics/unusual-spending")
def get_unusual(db: Session = Depends(get_db)):
    """Detect unusual transactions"""
    return analytics.get_unusual_spending(db)

@app.get("/analytics/savings-opportunities")
def get_savings(db: Session = Depends(get_db)):
    """Get savings recommendations"""
    return analytics.identify_savings_opportunities(db)

@app.get("/analytics/predict-spending")
def predict_spending(category: Optional[str] = None, db: Session = Depends(get_db)):
    """Predict next month's spending"""
    return analytics.predict_monthly_spending(db, category)

@app.get("/analytics/budget-alerts")
def get_alerts(db: Session = Depends(get_db)):
    """Get budget alerts"""
    return analytics.get_budget_alerts(db)

# ============= VISUALIZATION ENDPOINTS =============

@app.get("/visualizations/monthly-trend")
def get_monthly_trend_chart(months: int = 6, db: Session = Depends(get_db)):
    """Get monthly spending trend chart as base64 image"""
    img_base64 = visualizations.create_monthly_trend_chart(db, months)
    return {"image": img_base64, "format": "base64"}

@app.get("/visualizations/category-pie")
def get_category_pie_chart(limit: int = 5, db: Session = Depends(get_db)):
    """Get top categories pie chart as base64 image"""
    img_base64 = visualizations.create_category_pie_chart(db, limit)
    return {"image": img_base64, "format": "base64"}

@app.get("/visualizations/budget-comparison")
def get_budget_comparison_chart(db: Session = Depends(get_db)):
    """Get budget vs actual comparison chart as base64 image"""
    img_base64 = visualizations.create_budget_comparison_chart(db)
    return {"image": img_base64, "format": "base64"}

@app.get("/visualizations/spending-patterns")
def get_spending_patterns_chart(db: Session = Depends(get_db)):
    """Get spending patterns by day of week chart as base64 image"""
    img_base64 = visualizations.create_spending_patterns_chart(db)
    return {"image": img_base64, "format": "base64"}

@app.get("/visualizations/income-expense")
def get_income_expense_chart(months: int = 6, db: Session = Depends(get_db)):
    """Get income vs expense comparison chart as base64 image"""
    img_base64 = visualizations.create_income_expense_chart(db, months)
    return {"image": img_base64, "format": "base64"}

@app.get("/visualizations/category-trend/{category}")
def get_category_trend_chart(category: str, months: int = 6, db: Session = Depends(get_db)):
    """Get spending trend for specific category as base64 image"""
    img_base64 = visualizations.create_category_trend_chart(db, category, months)
    return {"image": img_base64, "format": "base64"}

# ============= EXPORT ENDPOINTS =============

@app.get("/export/transactions")
def export_transactions(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Export transactions to CSV"""
    csv_data = exports.export_transactions_csv(db, start_date, end_date)

    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=transactions_{date.today()}.csv"
        }
    )

@app.get("/export/budgets")
def export_budgets(db: Session = Depends(get_db)):
    """Export budgets to CSV"""
    csv_data = exports.export_budgets_csv(db)

    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=budgets_{date.today()}.csv"
        }
    )

@app.get("/export/summary")
def export_summary(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Export spending summary to CSV"""
    # 1. Get the string data from your export module
    csv_string = exports.export_summary_csv(db, start_date, end_date)

    # 2. Wrap it in a StringIO buffer
    output = io.StringIO()
    output.write(csv_string)
    output.seek(0) # Go back to the start of the file

    return StreamingResponse(
        output, # FastAPI handles file-like objects automatically
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=summary_{date.today()}.csv"
        }
    )
# ============= ML PREDICTION ENDPOINTS =============

@app.get("/predictions/next-month")
def predict_next_month(category_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Predict next month's spending (simple linear regression)"""
    return ml_predictions.predict_next_month_spending(db, category_id)

@app.get("/predictions/next-month-advanced")
def predict_next_month_advanced(category_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Predict next month's spending with seasonality (polynomial regression)"""
    return ml_predictions.predict_spending_with_seasonality(db, category_id)

@app.get("/predictions/by-category")
def predict_all_categories(db: Session = Depends(get_db)):
    """Predict spending for all categories"""
    return ml_predictions.predict_by_category(db)

@app.get("/predictions/budget-exhaustion/{category_id}")
def predict_budget_exhaustion(category_id: int, db: Session = Depends(get_db)):
    """Predict when a budget will be exhausted"""
    return ml_predictions.predict_budget_exhaustion(db, category_id)

@app.get("/predictions/next-year")
def forecast_next_year(db: Session = Depends(get_db)):
    """Forecast total spending for next 12 months"""
    return ml_predictions.forecast_next_year(db)

# --- QUICK AND DIRTY SEEDING LOGIC ---
from backend import models
from backend.database import engine, SessionLocal
from sqlalchemy import text

print("=" * 60)
print("🔥 RESETTING AND SEEDING DATABASE")
print("=" * 60)

# Step 1: Drop all tables
print("\n📋 Step 1: Dropping all tables...")
try:
    with engine.connect() as connection:
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))

        tables_to_drop = ['transactions', 'budgets', 'categories']
        for table in tables_to_drop:
            connection.execute(text(f"DROP TABLE IF EXISTS {table}"))
            print(f"  ✅ Dropped: {table}")

        connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        connection.commit()
    print("✅ All tables dropped!")
except Exception as e:
    print(f"⚠️ Drop tables error: {e}")

# Step 2: Create all tables
print("\n📋 Step 2: Creating tables...")
try:
    models.Base.metadata.create_all(bind=engine)
    print("✅ All tables created!")
except Exception as e:
    print(f"⚠️ Create tables error: {e}")

# Step 3: Seed data
print("\n📋 Step 3: Seeding data...")
try:
    session = SessionLocal()

    # Import and run seeding scripts
    import add_default_categories
    import add_sample_data
    import generate_ml_data

    print("✅ Database reset and seeded successfully!")
    session.close()
except Exception as e:
    print(f"⚠️ Seeding error: {e}")

print("\n" + "=" * 60)
print("🎉 DATABASE READY!")
print("=" * 60)
# -------------------------------------
