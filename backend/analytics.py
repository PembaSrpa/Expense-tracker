import pandas as pd
from sqlalchemy.orm import Session
from backend.models import Transaction, Budget, TransactionType
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List

# ============= HELPER FUNCTIONS =============

def transactions_to_dataframe(db: Session, start_date: Optional[date] = None,
                              end_date: Optional[date] = None) -> pd.DataFrame:
    """Convert transactions from database to pandas DataFrame"""
    query = db.query(Transaction)

    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)

    transactions = query.all()

    # Convert to list of dictionaries
    data = [{
        'id': t.id,
        'date': t.date,
        'amount': t.amount,
        'category': t.category_rel.name,
        'description': t.description,
        'type': t.transaction_type.value,
        'created_at': t.created_at
    } for t in transactions]

    # Create DataFrame
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date']) # Convert to datetime for easier manipulation
    return df


# ============= TREND ANALYSIS =============

def get_monthly_spending_trend(db: Session, months: int = 6) -> List[Dict]:
    """Get spending trend for the last N months"""
    end_date = date.today()
    start_date = end_date - timedelta(days=months * 30)

    df = transactions_to_dataframe(db, start_date, end_date)

    if df.empty:
        return []

    # Filter only expenses
    df_expenses = df[df['type'] == 'expense'].copy()

    # Group by month
    df_expenses['month'] = df_expenses['date'].dt.to_period('M')
    monthly = df_expenses.groupby('month')['amount'].sum().reset_index()
    monthly['month'] = monthly['month'].astype(str)

    return monthly.to_dict('records')


def get_category_trend(db: Session, category_name: str, months: int = 6) -> List[Dict]:
    """Get spending trend for a specific category"""
    end_date = date.today()
    start_date = end_date - timedelta(days=months * 30)

    df = transactions_to_dataframe(db, start_date, end_date)

    if df.empty:
        return []

    # Filter by category and expenses
    df_category = df[(df['category'] == category_name) & (df['type'] == 'expense')].copy()

    if df_category.empty:
        return []

    # Group by month
    df_category['month'] = df_category['date'].dt.to_period('M')
    monthly = df_category.groupby('month')['amount'].sum().reset_index()
    monthly['month'] = monthly['month'].astype(str)

    return monthly.to_dict('records')


def get_spending_patterns(db: Session) -> Dict:
    """Analyze spending patterns (weekday vs weekend, time of month)"""
    df = transactions_to_dataframe(db)

    if df.empty:
        return {"error": "No data available"}

    df_expenses = df[df['type'] == 'expense'].copy()

    if df_expenses.empty:
        return {"error": "No expense data available"}

    # Weekday vs Weekend
    df_expenses['is_weekend'] = df_expenses['date'].dt.dayofweek >= 5
    weekday_avg = df_expenses[~df_expenses['is_weekend']]['amount'].mean()
    weekend_avg = df_expenses[df_expenses['is_weekend']]['amount'].mean()

    # Day of week
    df_expenses['day_name'] = df_expenses['date'].dt.day_name()
    by_day = df_expenses.groupby('day_name')['amount'].sum().to_dict()

    # Time of month (beginning, middle, end)
    df_expenses['day_of_month'] = df_expenses['date'].dt.day
    df_expenses['period'] = pd.cut(df_expenses['day_of_month'],
                                    bins=[0, 10, 20, 31],
                                    labels=['Beginning', 'Middle', 'End'])
    by_period = df_expenses.groupby('period', observed=False)['amount'].sum().to_dict()

    return {
        'weekday_avg': float(weekday_avg) if pd.notna(weekday_avg) else 0,
        'weekend_avg': float(weekend_avg) if pd.notna(weekend_avg) else 0,
        'by_day_of_week': by_day,
        'by_month_period': {str(k): float(v) for k, v in by_period.items()}
    }


# ============= INSIGHTS =============

def get_top_spending_categories(db: Session, limit: int = 5,
                                start_date: Optional[date] = None,
                                end_date: Optional[date] = None) -> List[Dict]:
    """Get top spending categories"""
    df = transactions_to_dataframe(db, start_date, end_date)

    if df.empty:
        return []

    df_expenses = df[df['type'] == 'expense']

    top_categories = df_expenses.groupby('category')['amount'].sum()\
                                 .sort_values(ascending=False)\
                                 .head(limit)\
                                 .reset_index()

    return top_categories.to_dict('records')


def get_unusual_spending(db: Session, std_threshold: float = 2.0) -> List[Dict]:
    """Detect unusual transactions (outliers)"""
    df = transactions_to_dataframe(db)

    if df.empty or len(df) < 5:
        return []

    df_expenses = df[df['type'] == 'expense'].copy()

    if df_expenses.empty:
        return []

    # Calculate mean and standard deviation by category
    category_stats = df_expenses.groupby('category')['amount'].agg(['mean', 'std'])

    unusual = []
    for _, row in df_expenses.iterrows():
        category = row['category']
        if category in category_stats.index:
            mean = category_stats.loc[category, 'mean']
            std = category_stats.loc[category, 'std']

            if pd.notna(std) and std > 0:
                z_score = (row['amount'] - mean) / std
                if abs(z_score) > std_threshold:
                    unusual.append({
                        'id': int(row['id']),
                        'date': row['date'].strftime('%Y-%m-%d'),
                        'amount': float(row['amount']),
                        'category': row['category'],
                        'description': row['description'],
                        'z_score': float(z_score)
                    })

    return unusual


def identify_savings_opportunities(db: Session) -> List[Dict]:
    df = transactions_to_dataframe(db)
    if df.empty: return []

    df_expenses = df[df['type'] == 'expense'].copy()

    budgets = db.query(Budget).all()
    budget_dict = {b.category_rel.name: b.monthly_limit for b in budgets}

    df_expenses['month'] = df_expenses['date'].dt.to_period('M')
    monthly_avg = df_expenses.groupby('category')['amount'].mean()

    opportunities = []
    for category_name, avg_spending in monthly_avg.items():
        if category_name in budget_dict:
            limit = budget_dict[category_name]
            if avg_spending > limit * 0.9:
                opportunities.append({
                    'category': category_name,
                    'average_monthly_spending': float(avg_spending),
                    'budget': float(limit),
                    'potential_savings': float(max(0, avg_spending - limit)),
                    'recommendation': f"Consider reducing {category_name} spending"
                })

    return sorted(opportunities, key=lambda x: x['potential_savings'], reverse=True)


# ============= PREDICTIONS =============

def predict_monthly_spending(db: Session, category: Optional[str] = None) -> Dict:
    """Predict next month's spending based on historical data"""
    df = transactions_to_dataframe(db)

    if df.empty:
        return {"error": "No data available"}

    df_expenses = df[df['type'] == 'expense'].copy()

    if category:
        df_expenses = df_expenses[df_expenses['category'] == category]

    if df_expenses.empty:
        return {"error": "No expense data available"}

    # Group by month
    df_expenses['month'] = df_expenses['date'].dt.to_period('M')
    monthly = df_expenses.groupby('month')['amount'].sum()

    if len(monthly) < 2:
        return {"error": "Not enough historical data"}

    # Simple prediction: average of last 3 months
    recent_avg = monthly.tail(3).mean()
    overall_avg = monthly.mean()

    # Calculate trend (increasing or decreasing)
    if len(monthly) >= 3:
        recent = monthly.tail(3).mean()
        older = monthly.head(len(monthly) - 3).mean() if len(monthly) > 3 else recent
        trend = "increasing" if recent > older else "decreasing"
    else:
        trend = "stable"

    return {
        'predicted_amount': float(recent_avg),
        'overall_average': float(overall_avg),
        'trend': trend,
        'confidence': 'medium' if len(monthly) >= 6 else 'low'
    }


def get_budget_alerts(db: Session) -> List[Dict]:
    today = date.today()
    start_of_month = date(today.year, today.month, 1)

    df = transactions_to_dataframe(db, start_of_month, today)

    if df.empty:
        return []

    df_expenses = df[df['type'] == 'expense']
    current_spending = df_expenses.groupby('category')['amount'].sum()

    budgets = db.query(Budget).all()

    alerts = []
    for budget in budgets:
        category_name = budget.category_rel.name
        spent = current_spending.get(category_name, 0)

        percentage = (spent / budget.monthly_limit * 100) if budget.monthly_limit > 0 else 0

        alert_level = None
        if percentage >= 100:
            alert_level = 'critical'
        elif percentage >= 90:
            alert_level = 'warning'
        elif percentage >= 75:
            alert_level = 'info'

        if alert_level:
            alerts.append({
                'category': category_name,
                'budget': float(budget.monthly_limit),
                'spent': float(spent),
                'remaining': float(budget.monthly_limit - spent),
                'percentage': float(percentage),
                'alert_level': alert_level,
                'message': f"{percentage:.1f}% of budget used"
            })

    return sorted(alerts, key=lambda x: x['percentage'], reverse=True)
