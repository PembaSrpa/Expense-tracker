import pandas as pd
from sqlalchemy.orm import Session
from backend.models import Transaction, TransactionType
from datetime import date, timedelta
from typing import Optional, Dict, List

def transactions_to_dataframe(db: Session, start_date: Optional[date] = None, end_date: Optional[date] = None) -> pd.DataFrame:
    query = db.query(Transaction)
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    transactions = query.all()
    data = [{
        'id': t.id,
        'date': t.date,
        'amount': t.amount,
        'category': t.category_rel.name,
        'type': t.transaction_type.value
    } for t in transactions]
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    return df

def get_monthly_spending_trend(db: Session, months: int = 6) -> List[Dict]:
    end_date = date.today()
    start_date = end_date - timedelta(days=months * 30)
    df = transactions_to_dataframe(db, start_date, end_date)
    if df.empty:
        return []
    df_expenses = df[df['type'] == 'expense'].copy()
    df_expenses['month'] = df_expenses['date'].dt.to_period('M')
    monthly = df_expenses.groupby('month')['amount'].sum().reset_index()
    monthly['month'] = monthly['month'].astype(str)
    return monthly.to_dict('records')

def get_top_spending_categories(db: Session, limit: int = 5) -> List[Dict]:
    df = transactions_to_dataframe(db)
    if df.empty:
        return []
    df_expenses = df[df['type'] == 'expense']
    top_categories = df_expenses.groupby('category')['amount'].sum().sort_values(ascending=False).head(limit).reset_index()
    return top_categories.to_dict('records')

def get_spending_patterns(db: Session) -> Dict:
    df = transactions_to_dataframe(db)
    if df.empty: return {}
    df_expenses = df[df['type'] == 'expense'].copy()
    df_expenses['day_name'] = df_expenses['date'].dt.day_name()
    by_day = df_expenses.groupby('day_name')['amount'].sum().to_dict()
    return {'by_day_of_week': by_day}
