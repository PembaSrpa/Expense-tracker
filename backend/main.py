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

class TransactionCreate(BaseModel):
    date: date
    amount: float
    category_name: str
    description: Optional[str] = None
    transaction_type: TransactionType

class TransactionUpdate(BaseModel):
    date: Optional[date] = None # type: ignore
    amount: Optional[float] = None
    category_name: Optional[str] = None
    description: Optional[str] = None
    transaction_type: Optional[TransactionType] = None

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
    type: str

class CategoryResponse(BaseModel):
    id: int
    name: str
    type: str

    class Config:
        from_attributes = True

app = FastAPI(
    title="Expense Tracker API",
    description="API for tracking expenses and managing budgets",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hao"}

@app.post("/transactions", response_model=TransactionResponse)
def create_transaction(transaction: TransactionCreate, db: Session = Depends(get_db)):
    category = crud.get_category_by_name(db, transaction.category_name)
    if not category:
        available = [c.name for c in crud.get_categories(db)]
        raise HTTPException(
            status_code=404,
            detail=f"Category '{transaction.category_name}' not found. Available categories: {', '.join(available)}"
        )

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
    transaction = crud.get_transaction_by_id(db, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction

@app.put("/transactions/{transaction_id}", response_model=TransactionResponse)
def update_transaction(transaction_id: int, transaction: TransactionUpdate, db: Session = Depends(get_db)):
    update_data = transaction.dict(exclude_unset=True)

    if "category_name" in update_data:
        category = crud.get_category_by_name(db, name=update_data["category_name"])
        if not category:
            raise HTTPException(status_code=400, detail="Category not found")
        update_data["category_id"] = category.id
        del update_data["category_name"]

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
    success = crud.delete_transaction(db, transaction_id)
    if not success:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"message": "Transaction deleted successfully"}

@app.post("/categories", response_model=CategoryResponse)
def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    return crud.create_category(db, name=category.name, type=category.type)

@app.get("/categories", response_model=List[CategoryResponse])
def get_categories(type: Optional[str] = None, db: Session = Depends(get_db)):
    return crud.get_categories(db, type=type)

@app.post("/budgets", response_model=BudgetResponse)
def create_budget(budget: BudgetCreate, db: Session = Depends(get_db)):
    category = crud.get_category_by_name(db, budget.category_name)
    if not category:
        available = [c.name for c in crud.get_categories(db, type='expense')]
        raise HTTPException(
            status_code=404,
            detail=f"Category '{budget.category_name}' not found. Available: {', '.join(available)}"
        )

    existing_budget = crud.get_budget_by_category_id(db, category.id)
    if existing_budget:
        raise HTTPException(
            status_code=400,
            detail=f"A budget for '{budget.category_name}' already exists. Please update the existing one."
        )

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
    budgets = crud.get_budgets(db)
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
    category_obj = crud.get_category_by_name(db, category)
    if not category_obj:
        raise HTTPException(status_code=404, detail=f"Category '{category}' not found")

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
    success = crud.delete_budget(db, budget_id)
    if not success:
        raise HTTPException(status_code=404, detail="Budget not found")
    return {"message": "Budget deleted successfully"}

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
    return crud.get_budget_vs_actual(db, category_id, start_date, end_date)

@app.get("/analytics/monthly-trend")
def get_monthly_trend(months: int = 6, db: Session = Depends(get_db)):
    return analytics.get_monthly_spending_trend(db, months)

@app.get("/analytics/category-trend/{category}")
def get_category_trend_endpoint(category: str, months: int = 6, db: Session = Depends(get_db)):
    return analytics.get_category_trend(db, category, months)

@app.get("/analytics/spending-patterns")
def get_patterns(db: Session = Depends(get_db)):
    return analytics.get_spending_patterns(db)

@app.get("/analytics/top-categories")
def get_top_categories(limit: int = 5, db: Session = Depends(get_db)):
    return analytics.get_top_spending_categories(db, limit)

@app.get("/analytics/unusual-spending")
def get_unusual(db: Session = Depends(get_db)):
    return analytics.get_unusual_spending(db)

@app.get("/analytics/savings-opportunities")
def get_savings(db: Session = Depends(get_db)):
    return analytics.identify_savings_opportunities(db)

@app.get("/analytics/predict-spending")
def predict_spending(category: Optional[str] = None, db: Session = Depends(get_db)):
    return analytics.predict_monthly_spending(db, category)

@app.get("/analytics/budget-alerts")
def get_alerts(db: Session = Depends(get_db)):
    return analytics.get_budget_alerts(db)

@app.get("/visualizations/monthly-trend")
def get_monthly_trend_chart(months: int = 6, db: Session = Depends(get_db)):
    img_base64 = visualizations.create_monthly_trend_chart(db, months)
    return {"image": img_base64, "format": "base64"}

@app.get("/visualizations/category-pie")
def get_category_pie_chart(limit: int = 5, db: Session = Depends(get_db)):
    img_base64 = visualizations.create_category_pie_chart(db, limit)
    return {"image": img_base64, "format": "base64"}

@app.get("/visualizations/budget-comparison")
def get_budget_comparison_chart(db: Session = Depends(get_db)):
    img_base64 = visualizations.create_budget_comparison_chart(db)
    return {"image": img_base64, "format": "base64"}

@app.get("/visualizations/spending-patterns")
def get_spending_patterns_chart(db: Session = Depends(get_db)):
    img_base64 = visualizations.create_spending_patterns_chart(db)
    return {"image": img_base64, "format": "base64"}

@app.get("/visualizations/income-expense")
def get_income_expense_chart(months: int = 6, db: Session = Depends(get_db)):
    img_base64 = visualizations.create_income_expense_chart(db, months)
    return {"image": img_base64, "format": "base64"}

@app.get("/visualizations/category-trend/{category}")
def get_category_trend_chart(category: str, months: int = 6, db: Session = Depends(get_db)):
    img_base64 = visualizations.create_category_trend_chart(db, category, months)
    return {"image": img_base64, "format": "base64"}

@app.get("/export/transactions")
def export_transactions(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
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
    csv_string = exports.export_summary_csv(db, start_date, end_date)
    output = io.StringIO()
    output.write(csv_string)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=summary_{date.today()}.csv"
        }
    )

@app.get("/predictions/next-month")
def predict_next_month(category_id: Optional[int] = None, db: Session = Depends(get_db)):
    return ml_predictions.predict_next_month_spending(db, category_id)

@app.get("/predictions/next-month-advanced")
def predict_next_month_advanced(category_id: Optional[int] = None, db: Session = Depends(get_db)):
    return ml_predictions.predict_spending_with_seasonality(db, category_id)

@app.get("/predictions/by-category")
def predict_all_categories(db: Session = Depends(get_db)):
    return ml_predictions.predict_by_category(db)

@app.get("/predictions/budget-exhaustion/{category_id}")
def predict_budget_exhaustion(category_id: int, db: Session = Depends(get_db)):
    return ml_predictions.predict_budget_exhaustion(db, category_id)

@app.get("/predictions/next-year")
def forecast_next_year(db: Session = Depends(get_db)):
    return ml_predictions.forecast_next_year(db)
