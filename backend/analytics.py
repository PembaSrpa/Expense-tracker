import pandas as pd
from sqlalchemy.orm import Session
from backend.models import Transaction, TransactionType, Category, Budget
from datetime import date, timedelta, datetime
from typing import Optional, Dict, List
from sqlalchemy import func

def transactions_to_dataframe(db: Session, start_date: Optional[date] = None, end_date: Optional[date] = None) -> pd.DataFrame:
    query = db.query(Transaction)

    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)

    transactions = query.all()

    data = []
    for t in transactions:
        data.append({
            'id': t.id,
            'date': t.date,
            'amount': t.amount,
            'category': t.category_rel.name if t.category_rel else "Unknown",
            'category_id': t.category_id,
            'description': t.description,
            'type': t.transaction_type.value
        })

    if not data:
        return pd.DataFrame(columns=['id', 'date', 'amount', 'category', 'category_id', 'description', 'type'])

    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    return df

def get_monthly_spending_trend(db: Session, months: int = 6) -> List[Dict]:
    df = transactions_to_dataframe(db)
    if df.empty:
        return []

    df_expenses = df[df['type'] == 'expense'].copy()

    if df_expenses.empty:
        return []

    df_expenses['month'] = df_expenses['date'].dt.to_period('M')
    monthly_spending = df_expenses.groupby('month')['amount'].sum().reset_index()

    monthly_spending = monthly_spending.sort_values('month').tail(months)

    monthly_spending['month'] = monthly_spending['month'].astype(str)

    return monthly_spending.to_dict('records')

def get_top_spending_categories(db: Session, limit: int = 5, start_date=None, end_date=None) -> List[Dict]:
    df = transactions_to_dataframe(db, start_date, end_date)
    if df.empty:
        return []

    df_expenses = df[df['type'] == 'expense']
    if df_expenses.empty:
        return []

    category_spending = df_expenses.groupby('category')['amount'].sum().sort_values(ascending=False)

    return [{"category": cat, "amount": float(amt)} for cat, amt in category_spending.head(limit).items()]

def get_category_trend(db: Session, category: str, months: int = 6) -> List[Dict]:
    df = transactions_to_dataframe(db)
    if df.empty:
        return []

    df_category = df[(df['category'] == category) & (df['type'] == 'expense')].copy()
    if df_category.empty:
        return []

    df_category['month'] = df_category['date'].dt.to_period('M')
    monthly_trend = df_category.groupby('month')['amount'].sum().reset_index()
    monthly_trend = monthly_trend.sort_values('month').tail(months)
    monthly_trend['month'] = monthly_trend['month'].astype(str)

    return monthly_trend.to_dict('records')

def get_spending_patterns(db: Session) -> Dict:
    df = transactions_to_dataframe(db)
    if df.empty:
        return {}

    df_expenses = df[df['type'] == 'expense'].copy()
    if df_expenses.empty:
        return {}

    df_expenses['day_of_week'] = df_expenses['date'].dt.day_name()

    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    pattern = df_expenses.groupby('day_of_week')['amount'].sum().reindex(day_order).fillna(0)

    return pattern.to_dict()

def get_unusual_spending(db: Session, threshold_multiplier: float = 1.5) -> List[Dict]:
    df = transactions_to_dataframe(db)
    if df.empty:
        return []

    df_expenses = df[df['type'] == 'expense']
    if df_expenses.empty:
        return []

    cat_averages = df_expenses.groupby('category')['amount'].mean().to_dict()

    unusual = []
    for _, row in df_expenses.iterrows():
        avg = cat_averages.get(row['category'], 0)
        if row['amount'] > avg * threshold_multiplier and row['amount'] > 50:
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
    budgets = db.query(Budget).all()
    if not budgets:
        return []

    alerts = []
    current_date = datetime.now().date()
    month_start = current_date.replace(day=1)

    for budget in budgets:
        month_spending = db.query(func.sum(Transaction.amount)).filter(
            Transaction.category_id == budget.category_id,
            Transaction.transaction_type == TransactionType.expense,
            Transaction.date >= month_start,
            Transaction.date <= current_date
        ).scalar() or 0.0

        percentage_used = (month_spending / budget.monthly_limit) * 100 if budget.monthly_limit > 0 else 0

        alert_level = None
        message = None

        if percentage_used >= 100:
            alert_level = "critical"
            message = f"Budget exceeded by ${month_spending - budget.monthly_limit:.2f}"
        elif percentage_used >= 90:
            alert_level = "warning"
            message = f"90% of budget used. ${budget.monthly_limit - month_spending:.2f} remaining"
        elif percentage_used >= 80:
            alert_level = "info"
            message = f"80% of budget used. ${budget.monthly_limit - month_spending:.2f} remaining"

        if alert_level:
            alerts.append({
                "category": budget.category_rel.name if budget.category_rel else "Unknown",
                "category_id": budget.category_id,
                "budget_limit": float(budget.monthly_limit),
                "spent_so_far": float(month_spending),
                "percentage_used": round(percentage_used, 1),
                "remaining": round(float(budget.monthly_limit - month_spending), 2),
                "alert_level": alert_level,
                "message": message
            })

    return alerts

def identify_savings_opportunities(db: Session) -> List[Dict]:
    df = transactions_to_dataframe(db)
    if df.empty:
        return []

    df_expenses = df[df['type'] == 'expense']
    if df_expenses.empty:
        return []

    category_spending = df_expenses.groupby('category')['amount'].sum().sort_values(ascending=False)

    opportunities = []
    for category, total in category_spending.head(3).items():
        avg_per_transaction = df_expenses[df_expenses['category'] == category]['amount'].mean()
        opportunities.append({
            "category": category,
            "total_spent": round(float(total), 2),
            "average_per_transaction": round(float(avg_per_transaction), 2),
            "suggestion": f"Consider reviewing {category} expenses to identify savings"
        })

    return opportunities

def predict_monthly_spending(db: Session, category: Optional[str] = None) -> Dict:
    df = transactions_to_dataframe(db)
    if df.empty:
        return {"predicted_spending": 0, "confidence": "low", "based_on_months": 0}

    df_expenses = df[df['type'] == 'expense'].copy()
    if df_expenses.empty:
        return {"predicted_spending": 0, "confidence": "low", "based_on_months": 0}

    if category:
        df_expenses = df_expenses[df_expenses['category'] == category]
        if df_expenses.empty:
            return {
                "category": category,
                "predicted_spending": 0,
                "confidence": "low",
                "message": "No historical data for this category"
            }

    df_expenses['month'] = df_expenses['date'].dt.to_period('M')
    monthly_totals = df_expenses.groupby('month')['amount'].sum()

    avg_spending = monthly_totals.mean()
    months_of_data = len(monthly_totals)

    if months_of_data >= 6:
        confidence = "high"
    elif months_of_data >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    result = {
        "predicted_spending": round(float(avg_spending), 2),
        "confidence": confidence,
        "based_on_months": months_of_data,
        "monthly_average": round(float(avg_spending), 2)
    }

    if category:
        result["category"] = category

    return result
