import pandas as pd
from sklearn.linear_model import LinearRegression
from sqlalchemy.orm import Session
from backend.models import Transaction, TransactionType
from datetime import date, timedelta
from typing import Optional, Dict

def get_monthly_spending_data(db: Session, category_id: Optional[int] = None) -> pd.DataFrame:
    end_date = date.today()
    start_date = end_date - timedelta(days=365)
    query = db.query(Transaction).filter(
        Transaction.date >= start_date,
        Transaction.transaction_type == TransactionType.expense
    )
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    transactions = query.all()
    if not transactions: return pd.DataFrame()
    df = pd.DataFrame([{'date': t.date, 'amount': t.amount} for t in transactions])
    df['month'] = pd.to_datetime(df['date']).dt.to_period('M')
    monthly = df.groupby('month')['amount'].sum().reset_index()
    monthly['month_num'] = range(len(monthly))
    return monthly

def predict_next_month_spending(db: Session, category_id: Optional[int] = None) -> Dict:
    df = get_monthly_spending_data(db, category_id)
    if len(df) < 3: return {"error": "Low data"}
    X = df['month_num'].values.reshape(-1, 1)
    y = df['amount'].values
    model = LinearRegression().fit(X, y)
    prediction = model.predict([[len(df)]])[0]
    return {"predicted_amount": float(max(0, prediction)), "accuracy": float(model.score(X, y))}
