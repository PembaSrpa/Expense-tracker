import pandas as pd
from sqlalchemy.orm import Session
from backend.models import Transaction, TransactionType, Category, Budget
from datetime import date, timedelta
from typing import Optional, Dict, List
from sqlalchemy import func

def transactions_to_dataframe(db: Session, start_date: Optional[date] = None, end_date: Optional[date] = None) -> pd.DataFrame:
    # Query transactions with category information
    query = db.query(Transaction)

    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)

    transactions = query.all()

    # Convert to list of dicts for DataFrame
    data = []
    for t in transactions:
        data.append({
            'id': t.id,
            'date': t.date,
            'amount': t.amount,
            'category': t.category_rel.name if t.category_rel else "Unknown",
            'category_id': t.category_id,
            'description': t.description,
            'type': t.transaction_type.value # 'income' or 'expense'
        })

    if not data:
        return pd.DataFrame(columns=['id', 'date', 'amount', 'category', 'category_id', 'description', 'type'])

    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    return df

def get_monthly_spending_trend(db: Session, months: int = 6) -> List[Dict]:
    """Calculates total spending per month for the last N months"""
    df = transactions_to_dataframe(db)
    if df.empty:
        return []

    # Filter for expenses only
    df_expenses = df[df['type'] == 'expense'].copy()

    if df_expenses.empty:
        return []

    # Group by month
    df_expenses['month'] = df_expenses['date'].dt.to_period('M')
    monthly_spending = df_expenses.groupby('month')['amount'].sum().reset_index()

    # Sort and take last N months
    monthly_spending = monthly_spending.sort_values('month').tail(months)

    # Convert month period to string for JSON serialization
    monthly_spending['month'] = monthly_spending['month'].astype(str)

    return monthly_spending.to_dict('records')

def get_top_spending_categories(db: Session, limit: int = 5, start_date=None, end_date=None) -> List[Dict]:
    """Identifies categories with the highest total spending"""
    df = transactions_to_dataframe(db, start_date, end_date)
    if df.empty:
        return []

    df_expenses = df[df['type'] == 'expense']
    if df_expenses.empty:
        return []

    category_spending = df_expenses.groupby('category')['amount'].sum().sort_values(ascending=False)

    return [{"category": cat, "amount": float(amt)} for cat, amt in category_spending.head(limit).items()]

def get_spending_patterns(db: Session) -> Dict:
    """Analyzes spending by day of the week"""
    df = transactions_to_dataframe(db)
    if df.empty:
        return {}

    df_expenses = df[df['type'] == 'expense'].copy()
    if df_expenses.empty:
        return {}

    df_expenses['day_of_week'] = df_expenses['date'].dt.day_name()

    # Average spending per day of week
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    pattern = df_expenses.groupby('day_of_week')['amount'].sum().reindex(day_order).fillna(0)

    return pattern.to_dict()

def get_unusual_spending(db: Session, threshold_multiplier: float = 1.5) -> List[Dict]:
    """Identifies transactions that are significantly higher than the category average"""
    df = transactions_to_dataframe(db)
    if df.empty:
        return []

    df_expenses = df[df['type'] == 'expense']
    if df_expenses.empty:
        return []

    # Calculate average per category
    cat_averages = df_expenses.groupby('category')['amount'].mean().to_dict()

    unusual = []
    for _, row in df_expenses.iterrows():
        avg = cat_averages.get(row['category'], 0)
        if row['amount'] > avg * threshold_multiplier and row['amount'] > 50: # Only care about $50+
            unusual.append({
                'id': int(row['id']),
                'date': row['date'].strftime('%Y-%m-%d'),
                'category': row['category'],
                'amount': float(row['amount']),
                'average_for_category': round(float(avg), 2),
                'description': row['description']
            })

    return unusual

def get_budget_alerts(db: Session) -> List[Dict]:
    """Returns alerts for categories that are close to or over budget"""
    # This logic would compare current month's spending with active budgets
    # Implementation depends on budget model structure
    return []

def identify_savings_opportunities(db: Session) -> List[Dict]:
    """Finds recurring high expenses that could be reduced"""
    df = transactions_to_dataframe(db)
    if df.empty:
        return []

    # Look for high-frequency, high-cost categories
    # For now, just a placeholder
    return [{"category": "Dining Out", "suggestion": "Try meal prepping to save up to $200/month"}]
