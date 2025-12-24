from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import crud
from backend.models import TransactionType
from pydantic import BaseModel
from datetime import date
from typing import Optional, List

# Pydantic models for request/response validation

class TransactionCreate(BaseModel):
    date: date
    amount: float
    category: str
    description: Optional[str] = None
    transaction_type: TransactionType

class TransactionResponse(BaseModel):
    id: int
    date: date
    amount: float
    category: str
    description: Optional[str]
    transaction_type: TransactionType

    class Config:
        from_attributes = True  # Allows Pydantic to work with SQLAlchemy models

class BudgetCreate(BaseModel):
    category: str
    monthly_limit: float
    start_date: date

class BudgetResponse(BaseModel):
    id: int
    category: str
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
        category=transaction.category,
        description=transaction.description,
        transaction_type=transaction.transaction_type
    )

@app.get("/transactions", response_model=List[TransactionResponse])
def get_transactions(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
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
        category=category,
        start_date=start_date,
        end_date=end_date,
        transaction_type=transaction_type
    )

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
        category=budget.category,
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

@app.get("/analytics/budget-vs-actual/{category}")
def get_budget_comparison(
    category: str,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):
    """Compare budget to actual spending"""
    return crud.get_budget_vs_actual(db, category, start_date, end_date)

# ============= ADDITIONAL TRANSACTION ENDPOINTS =============

@app.put("/transactions/{transaction_id}", response_model=TransactionResponse)
def update_transaction(transaction_id: int, transaction: TransactionCreate, db: Session = Depends(get_db)):
    """Update an existing transaction"""
    updated = crud.update_transaction(db, transaction_id, **transaction.dict(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return updated

# ============= ADDITIONAL BUDGET ENDPOINTS =============

@app.delete("/budgets/{budget_id}")
def delete_budget(budget_id: int, db: Session = Depends(get_db)):
    """Delete a budget"""
    success = crud.delete_budget(db, budget_id)
    if not success:
        raise HTTPException(status_code=404, detail="Budget not found")
    return {"message": "Budget deleted successfully"}

# ============= CATEGORY ENDPOINTS =============

@app.post("/categories", response_model=CategoryResponse)
def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    """Create a new category"""
    return crud.create_category(db, name=category.name, type=category.type)

@app.get("/categories", response_model=List[CategoryResponse])
def get_categories(type: Optional[str] = None, db: Session = Depends(get_db)):
    """Get all categories, optionally filtered by type"""
    return crud.get_categories(db, type=type)
