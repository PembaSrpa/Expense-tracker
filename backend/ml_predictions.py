import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sqlalchemy.orm import Session
from backend.models import Transaction, TransactionType
from datetime import date, timedelta
from typing import Optional, Dict, List
import warnings
warnings.filterwarnings('ignore')


# ============= HELPER FUNCTIONS =============

def get_monthly_spending_data(db: Session, category_id: Optional[int] = None,
                              months_back: int = 12) -> pd.DataFrame:
    """Get historical monthly spending data"""
    end_date = date.today()
    start_date = end_date - timedelta(days=months_back * 30)

    query = db.query(Transaction).filter(
        Transaction.date >= start_date,
        Transaction.date <= end_date,
        Transaction.transaction_type == TransactionType.expense
    )

    if category_id:
        query = query.filter(Transaction.category_id == category_id)

    transactions = query.all()

    if not transactions:
        return pd.DataFrame()

    # Convert to DataFrame
    data = [{
        'date': t.date,
        'amount': t.amount,
        'category_id': t.category_id
    } for t in transactions]

    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.to_period('M')

    # Group by month
    monthly = df.groupby('month')['amount'].sum().reset_index()
    monthly['month_num'] = range(len(monthly))  # 0, 1, 2, 3...

    return monthly


# ============= PREDICTION FUNCTIONS =============

def predict_next_month_spending(db: Session, category_id: Optional[int] = None) -> Dict:
    """
    Predict next month's spending using Linear Regression

    Returns:
        - predicted_amount: Predicted spending
        - confidence: low/medium/high based on data quality
        - trend: increasing/decreasing/stable
        - historical_avg: Average spending
        - model_accuracy: R² score
    """

    # Get historical data
    df = get_monthly_spending_data(db, category_id, months_back=12)

    if df.empty or len(df) < 3:
        return {
            "error": "Insufficient data for prediction (need at least 3 months)",
            "predicted_amount": None,
            "confidence": "none"
        }

    # Prepare data for ML
    X = df['month_num'].values.reshape(-1, 1)  # Month numbers
    y = df['amount'].values  # Spending amounts

    # Train Linear Regression model
    model = LinearRegression()
    model.fit(X, y)

    # Predict next month
    next_month_num = len(df)
    predicted_amount = model.predict([[next_month_num]])[0]

    # Calculate model accuracy (R² score)
    r2_score = model.score(X, y)

    # Determine confidence level
    if len(df) >= 12 and r2_score >= 0.7:
        confidence = "high"
    elif len(df) >= 6 and r2_score >= 0.5:
        confidence = "medium"
    else:
        confidence = "low"

    # Determine trend
    if model.coef_[0] > 10:  # Slope > 10 means increasing
        trend = "increasing"
    elif model.coef_[0] < -10:  # Slope < -10 means decreasing
        trend = "decreasing"
    else:
        trend = "stable"

    # Calculate statistics
    historical_avg = float(y.mean())
    historical_min = float(y.min())
    historical_max = float(y.max())

    # Ensure prediction is not negative
    predicted_amount = max(0, predicted_amount)

    return {
        "predicted_amount": float(predicted_amount),
        "confidence": confidence,
        "trend": trend,
        "historical_avg": historical_avg,
        "historical_min": historical_min,
        "historical_max": historical_max,
        "model_accuracy": float(r2_score),
        "data_points": len(df),
        "recommendation": _generate_recommendation(predicted_amount, historical_avg, trend)
    }


def predict_spending_with_seasonality(db: Session, category_id: Optional[int] = None) -> Dict:
    """
    Advanced prediction considering seasonal patterns (polynomial regression)
    """

    df = get_monthly_spending_data(db, category_id, months_back=24)  # 2 years for seasonality

    if df.empty or len(df) < 6:
        return predict_next_month_spending(db, category_id)  # Fall back to simple prediction

    # Prepare data
    X = df['month_num'].values.reshape(-1, 1)
    y = df['amount'].values

    # Use Polynomial features to capture seasonality
    poly = PolynomialFeatures(degree=2)
    X_poly = poly.fit_transform(X)

    # Train model
    model = LinearRegression()
    model.fit(X_poly, y)

    # Predict next month
    next_month_num = len(df)
    X_next = poly.transform([[next_month_num]])
    predicted_amount = model.predict(X_next)[0]

    # Calculate accuracy
    r2_score = model.score(X_poly, y)

    # Determine confidence
    if len(df) >= 18 and r2_score >= 0.7:
        confidence = "high"
    elif len(df) >= 12 and r2_score >= 0.5:
        confidence = "medium"
    else:
        confidence = "low"

    # Predict trend for next 3 months
    future_months = []
    for i in range(1, 4):
        X_future = poly.transform([[next_month_num + i]])
        future_amount = model.predict(X_future)[0]
        future_months.append(max(0, float(future_amount)))

    predicted_amount = max(0, predicted_amount)

    return {
        "predicted_next_month": float(predicted_amount),
        "predicted_3_months": future_months,
        "confidence": confidence,
        "model_accuracy": float(r2_score),
        "data_points": len(df),
        "historical_avg": float(y.mean()),
        "uses_seasonality": True
    }


def predict_by_category(db: Session) -> List[Dict]:
    """
    Predict spending for all categories with sufficient data
    """
    from backend.crud import get_categories

    categories = get_categories(db, type='expense')
    predictions = []

    for category in categories:
        prediction = predict_next_month_spending(db, category.id)

        if not prediction.get('error'):
            predictions.append({
                "category_id": category.id,
                "category_name": category.name,
                **prediction
            })

    # Sort by predicted amount (highest first)
    predictions.sort(key=lambda x: x['predicted_amount'], reverse=True)

    return predictions


def predict_budget_exhaustion(db: Session, category_id: int) -> Dict:
    """
    Predict when a budget will be exhausted based on current spending rate
    """
    from backend.crud import get_budget_by_category_id
    from datetime import datetime

    # Get budget
    budget = get_budget_by_category_id(db, category_id)
    if not budget:
        return {"error": "No budget set for this category"}

    # Get current month spending
    today = date.today()
    start_of_month = date(today.year, today.month, 1)

    transactions = db.query(Transaction).filter(
        Transaction.category_id == category_id,
        Transaction.transaction_type == TransactionType.expense,
        Transaction.date >= start_of_month,
        Transaction.date <= today
    ).all()

    if not transactions:
        return {
            "days_remaining": "N/A",
            "exhaustion_date": None,
            "message": "No spending this month yet"
        }

    # Calculate daily spending rate
    current_spending = sum(t.amount for t in transactions)
    days_elapsed = (today - start_of_month).days + 1
    daily_rate = current_spending / days_elapsed

    # Calculate remaining budget
    remaining_budget = budget.monthly_limit - current_spending

    if remaining_budget <= 0:
        return {
            "budget_status": "exhausted",
            "over_budget_by": abs(remaining_budget),
            "message": f"Budget already exceeded by ${abs(remaining_budget):.2f}"
        }

    # Predict when budget will be exhausted
    days_until_exhaustion = remaining_budget / daily_rate if daily_rate > 0 else float('inf')
    exhaustion_date = today + timedelta(days=int(days_until_exhaustion))

    # Get last day of month
    if today.month == 12:
        last_day = date(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(today.year, today.month + 1, 1) - timedelta(days=1)

    return {
        "budget_limit": float(budget.monthly_limit),
        "current_spending": float(current_spending),
        "remaining_budget": float(remaining_budget),
        "daily_spending_rate": float(daily_rate),
        "days_until_exhaustion": int(days_until_exhaustion),
        "exhaustion_date": exhaustion_date.isoformat() if exhaustion_date <= last_day else None,
        "will_exceed_budget": exhaustion_date <= last_day,
        "message": _generate_exhaustion_message(days_until_exhaustion, exhaustion_date, last_day)
    }


def forecast_next_year(db: Session) -> Dict:
    """
    Forecast total spending for the next 12 months
    """

    df = get_monthly_spending_data(db, category_id=None, months_back=24)

    if df.empty or len(df) < 6:
        return {"error": "Insufficient data for yearly forecast"}

    # Use polynomial regression for better long-term prediction
    X = df['month_num'].values.reshape(-1, 1)
    y = df['amount'].values

    poly = PolynomialFeatures(degree=2)
    X_poly = poly.fit_transform(X)

    model = LinearRegression()
    model.fit(X_poly, y)

    # Predict next 12 months
    next_year_predictions = []
    start_month_num = len(df)

    for i in range(12):
        month_num = start_month_num + i
        X_future = poly.transform([[month_num]])
        predicted = model.predict(X_future)[0]
        next_year_predictions.append(max(0, float(predicted)))

    total_predicted = sum(next_year_predictions)
    avg_monthly = total_predicted / 12

    return {
        "total_predicted_spending": total_predicted,
        "avg_monthly_spending": avg_monthly,
        "monthly_predictions": next_year_predictions,
        "confidence": "medium" if len(df) >= 12 else "low",
        "based_on_months": len(df)
    }


# ============= HELPER FUNCTIONS =============

def _generate_recommendation(predicted: float, avg: float, trend: str) -> str:
    """Generate spending recommendation"""

    diff_percent = ((predicted - avg) / avg * 100) if avg > 0 else 0

    if trend == "increasing" and diff_percent > 10:
        return f"Spending is trending upward. Predicted ${predicted:.2f} vs average ${avg:.2f}. Consider reviewing expenses."
    elif trend == "decreasing":
        return f"Great! Spending is trending downward. Keep up the good habits!"
    elif abs(diff_percent) < 5:
        return f"Spending is stable around ${avg:.2f} per month."
    else:
        return f"Predicted spending: ${predicted:.2f}"


def _generate_exhaustion_message(days_until: float, exhaustion_date: date, last_day: date) -> str:
    """Generate budget exhaustion message"""

    if exhaustion_date <= last_day:
        if days_until <= 5:
            return f"⚠️ ALERT: Budget will be exhausted in {int(days_until)} days!"
        elif days_until <= 10:
            return f"⚠️ WARNING: Budget will be exhausted around {exhaustion_date.strftime('%B %d')}"
        else:
            return f"Budget on track to be exhausted by {exhaustion_date.strftime('%B %d')}"
    else:
        return "✅ Budget is safe for this month at current spending rate"
