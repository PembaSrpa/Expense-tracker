from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import crud
from backend.models import TransactionType
from pydantic import BaseModel
from datetime import date
from typing import Optional, List
from backend import analytics
from backend import visualizations
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from backend import exports
from fastapi.responses import StreamingResponse

# Pydantic models for request/response validation

class TransactionCreate(BaseModel):
    date: date
    amount: float
    category_id: int
    description: Optional[str] = None
    transaction_type: TransactionType

class TransactionResponse(BaseModel):
    id: int
    date: date
    amount: float
    category_id: int
    description: Optional[str]
    transaction_type: TransactionType

    class Config:
        from_attributes = True  # Allows Pydantic to work with SQLAlchemy models

class BudgetCreate(BaseModel):
    category_id: int
    monthly_limit: float
    start_date: date

class BudgetResponse(BaseModel):
    id: int
    category_id: int
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
    return crud.create_transaction(
        db=db,
        date=transaction.date,
        amount=transaction.amount,
        category_id=transaction.category_id,
        description=transaction.description,
        transaction_type=transaction.transaction_type
    )

@app.get("/transactions", response_model=List[TransactionResponse])
def get_transactions(
    skip: int = 0,
    limit: int = 100,
    category_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    transaction_type: Optional[TransactionType] = None,
    db: Session = Depends(get_db)
):
    """Get all transactions with optional filters"""
    return crud.get_transactions(
        db=db,
        skip=skip,
        limit=limit,
        category_id=category_id,
        start_date=start_date,
        end_date=end_date,
        transaction_type=transaction_type
    )

@app.put("/transactions/{transaction_id}", response_model=TransactionResponse)
def update_transaction(transaction_id: int, transaction: TransactionCreate, db: Session = Depends(get_db)):
    """Update an existing transaction"""
    updated = crud.update_transaction(
        db,
        transaction_id,
        date=transaction.date,
        amount=transaction.amount,
        category_id=transaction.category_id,  # CHANGED
        description=transaction.description,
        transaction_type=transaction.transaction_type
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return updated

@app.get("/transactions/{transaction_id}", response_model=TransactionResponse)
def get_transaction(transaction_id: int, db: Session = Depends(get_db)):
    """Get a specific transaction by ID"""
    transaction = crud.get_transaction_by_id(db, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction

@app.delete("/transactions/{transaction_id}")
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    """Delete a transaction"""
    success = crud.delete_transaction(db, transaction_id)
    if not success:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"message": "Transaction deleted successfully"}

# ============= BUDGET ENDPOINTS =============

@app.post("/budgets", response_model=BudgetResponse)
def create_budget(budget: BudgetCreate, db: Session = Depends(get_db)):
    """Create a new budget"""
    return crud.create_budget(
        db=db,
        category_id=budget.category_id,
        monthly_limit=budget.monthly_limit,
        start_date=budget.start_date
    )

@app.get("/budgets", response_model=List[BudgetResponse])
def get_budgets(db: Session = Depends(get_db)):
    """Get all budgets"""
    return crud.get_budgets(db)

@app.get("/budgets/{category}")
def get_budget(category: str, db: Session = Depends(get_db)):
    """Get budget for a specific category"""
    budget = crud.get_budget_by_category(db, category)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    return budget

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
    """Get spending grouped by category"""
    results = crud.get_spending_by_category(db, start_date, end_date)
    return [{"category": r.category, "total": r.total} for r in results]

@app.get("/analytics/income-expense")
def get_income_expense(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Get total income and expenses"""
    return crud.get_total_income_expense(db, start_date, end_date)

@app.get("/analytics/budget-vs-actual/{category_id}")
def get_budget_comparison(
    category_id: int,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):
    """Compare budget to actual spending"""
    return crud.get_budget_vs_actual(db, category_id, start_date, end_date)

# ============= CATEGORY ENDPOINTS =============

@app.post("/categories", response_model=CategoryResponse)
def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    """Create a new category"""
    return crud.create_category(db, name=category.name, type=category.type)

@app.get("/categories", response_model=List[CategoryResponse])
def get_categories(type: Optional[str] = None, db: Session = Depends(get_db)):
    """Get all categories, optionally filtered by type"""
    return crud.get_categories(db, type=type)

# ============= ADVANCED ANALYTICS ENDPOINTS =============

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
    csv_data = exports.export_summary_csv(db, start_date, end_date)

    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=summary_{date.today()}.csv"
        }
    )
