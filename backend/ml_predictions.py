import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sqlalchemy.orm import Session
from backend.models import Transaction, TransactionType, Category
from datetime import date, datetime, timedelta
from typing import Optional, Dict, List
from backend import analytics

def get_monthly_spending_data(db: Session, category_id: Optional[int] = None) -> pd.DataFrame:
    """Gets historical monthly totals for linear regression"""
    # Get the last 12 months of data
    end_date = date.today()
    start_date = end_date - timedelta(days=365)

    query = db.query(Transaction).filter(
        Transaction.date >= start_date,
        Transaction.transaction_type == TransactionType.expense
    )

    if category_id:
        query = query.filter(Transaction.category_id == category_id)

    transactions = query.all()

    if not transactions:
        return pd.DataFrame()

    data = [{'date': t.date, 'amount': t.amount} for t in transactions]
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])

    # Resample to monthly totals
    df.set_index('date', inplace=True)
    monthly = df.resample('M')['amount'].sum().reset_index()

    # Add a month index (0, 1, 2...) for regression
    monthly['month_index'] = range(len(monthly))

    return monthly

def predict_next_month_spending(db: Session, category_id: Optional[int] = None) -> Dict:
    """Predicts spending for next month using Simple Linear Regression"""
    df = get_monthly_spending_data(db, category_id)

    if len(df) < 3:
        return {
            "predicted_amount": 0,
            "confidence": 0,
            "message": "Not enough historical data (need at least 3 months)"
        }

    # Prepare data for Scikit-learn
    X = df[['month_index']].values
    y = df['amount'].values

    # Train model
    model = LinearRegression()
    model.fit(X, y)

    # Predict next month (next index)
    next_month_index = len(df)
    prediction = model.predict([[next_month_index]])[0]

    # Calculate R-squared for confidence
    r_squared = model.score(X, y)

    return {
        "predicted_amount": round(float(max(0, prediction)), 2),
        "confidence": round(float(r_squared), 2),
        "data_points": len(df)
    }

def predict_by_category(db: Session) -> List[Dict]:
    """Provides predictions for all major expense categories"""
    categories = db.query(Category).filter(Category.type == 'expense').all()
    predictions = []

    for cat in categories:
        pred = predict_next_month_spending(db, cat.id)
        if pred.get("predicted_amount", 0) > 0:
            predictions.append({
                "category": cat.name,
                "prediction": pred
            })

    return predictions

def predict_budget_exhaustion(db: Session, category_id: int) -> Dict:
    """Predicts when a user will hit their budget limit based on current velocity"""
    # This would calculate the current daily spend rate vs the monthly budget
    return {"message": "Prediction model under development"}

def predict_spending_with_seasonality(db: Session, category_id: Optional[int] = None) -> Dict:
    """More advanced prediction that accounts for seasonal trends"""
    # Placeholder for more complex model
    return predict_next_month_spending(db, category_id)

def forecast_next_year(db: Session) -> Dict:
    """Long-term spending forecast"""
    # Placeholder
    return {"message": "Yearly forecast requires more historical data"}
