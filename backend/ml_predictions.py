import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sqlalchemy.orm import Session
from backend.models import Transaction, TransactionType, Category, Budget
from datetime import date, datetime, timedelta
from typing import Optional, Dict, List
from sqlalchemy import func

def get_monthly_spending_data(db: Session, category_id: Optional[int] = None) -> pd.DataFrame:
    """Gets historical monthly totals for linear regression"""
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

    df.set_index('date', inplace=True)
    monthly = df.resample('M')['amount'].sum().reset_index()

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

    X = df[['month_index']].values
    y = df['amount'].values

    model = LinearRegression()
    model.fit(X, y)

    next_month_index = len(df)
    prediction = model.predict([[next_month_index]])[0]

    r_squared = model.score(X, y)

    return {
        "predicted_amount": round(float(max(0, prediction)), 2),
        "confidence": round(float(r_squared), 2),
        "data_points": len(df),
        "trend": "increasing" if model.coef_[0] > 0 else "decreasing",
        "monthly_change": round(float(model.coef_[0]), 2)
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
                "category_id": cat.id,
                "prediction": pred
            })

    predictions.sort(key=lambda x: x['prediction']['predicted_amount'], reverse=True)

    return predictions

def predict_budget_exhaustion(db: Session, category_id: int) -> Dict:
    """
    Predicts when a user will hit their budget limit based on current velocity.
    Calculates daily spending rate and estimates days until budget is exhausted.
    """
    budget = db.query(Budget).filter(Budget.category_id == category_id).first()

    if not budget:
        return {
            "error": "No budget found for this category",
            "exhaustion_date": None
        }

    current_date = date.today()
    month_start = current_date.replace(day=1)

    month_spending = db.query(func.sum(Transaction.amount)).filter(
        Transaction.category_id == category_id,
        Transaction.transaction_type == TransactionType.expense,
        Transaction.date >= month_start,
        Transaction.date <= current_date
    ).scalar() or 0.0

    days_elapsed = (current_date - month_start).days + 1

    if days_elapsed == 0:
        return {
            "error": "Not enough data for current month",
            "exhaustion_date": None
        }

    daily_rate = month_spending / days_elapsed

    remaining_budget = budget.monthly_limit - month_spending

    if remaining_budget <= 0:
        return {
            "status": "already_exhausted",
            "budget_limit": float(budget.monthly_limit),
            "spent_so_far": float(month_spending),
            "over_budget_by": float(abs(remaining_budget)),
            "exhaustion_date": current_date.isoformat()
        }

    if daily_rate <= 0:
        return {
            "status": "no_spending",
            "message": "No spending detected in current month",
            "exhaustion_date": None
        }

    days_until_exhaustion = remaining_budget / daily_rate
    exhaustion_date = current_date + timedelta(days=int(days_until_exhaustion))

    days_left_in_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    days_remaining_in_month = (days_left_in_month - current_date).days

    will_exceed = days_until_exhaustion < days_remaining_in_month

    return {
        "status": "on_track" if not will_exceed else "will_exceed",
        "budget_limit": float(budget.monthly_limit),
        "spent_so_far": float(month_spending),
        "remaining_budget": float(remaining_budget),
        "daily_spending_rate": round(float(daily_rate), 2),
        "days_until_exhaustion": int(days_until_exhaustion),
        "estimated_exhaustion_date": exhaustion_date.isoformat() if will_exceed else None,
        "will_exceed_budget": will_exceed,
        "days_left_in_month": days_remaining_in_month,
        "projected_month_end_spending": round(float(month_spending + (daily_rate * days_remaining_in_month)), 2)
    }

def predict_spending_with_seasonality(db: Session, category_id: Optional[int] = None) -> Dict:
    """
    More advanced prediction that accounts for seasonal trends.
    Uses last 12 months to detect patterns.
    """
    df = get_monthly_spending_data(db, category_id)

    if len(df) < 6:
        return {
            "predicted_amount": 0,
            "confidence": 0,
            "message": "Need at least 6 months of data for seasonality analysis"
        }

    if len(df) >= 12:
        recent_months = df.tail(12).copy()
    else:
        recent_months = df.copy()

    current_month = datetime.now().month

    same_month_data = recent_months[recent_months['date'].dt.month == current_month]

    if len(same_month_data) > 0:
        seasonal_avg = same_month_data['amount'].mean()
    else:
        seasonal_avg = recent_months['amount'].mean()

    overall_avg = recent_months['amount'].mean()

    recent_trend = recent_months.tail(3)['amount'].mean()

    X = recent_months[['month_index']].values
    y = recent_months['amount'].values

    model = LinearRegression()
    model.fit(X, y)

    next_month_index = len(df)
    linear_prediction = model.predict([[next_month_index]])[0]

    weighted_prediction = (
        0.4 * seasonal_avg +
        0.3 * linear_prediction +
        0.3 * recent_trend
    )

    r_squared = model.score(X, y)

    return {
        "predicted_amount": round(float(max(0, weighted_prediction)), 2),
        "confidence": round(float(r_squared), 2),
        "seasonal_average": round(float(seasonal_avg), 2),
        "linear_trend_prediction": round(float(linear_prediction), 2),
        "recent_3_month_avg": round(float(recent_trend), 2),
        "data_points": len(df),
        "method": "weighted_seasonal"
    }

def forecast_next_year(db: Session) -> Dict:
    """
    Long-term spending forecast for next 12 months.
    Predicts monthly spending and provides yearly total.
    """
    df = get_monthly_spending_data(db)

    if len(df) < 6:
        return {
            "error": "Need at least 6 months of historical data",
            "forecast": []
        }

    X = df[['month_index']].values
    y = df['amount'].values

    model = LinearRegression()
    model.fit(X, y)

    r_squared = model.score(X, y)

    forecasts = []
    total_forecast = 0

    for i in range(1, 13):
        next_month_index = len(df) + i - 1
        prediction = model.predict([[next_month_index]])[0]

        prediction = max(0, prediction)

        total_forecast += prediction

        forecast_date = datetime.now().replace(day=1) + timedelta(days=32 * i)
        forecast_date = forecast_date.replace(day=1)

        forecasts.append({
            "month": forecast_date.strftime("%Y-%m"),
            "predicted_amount": round(float(prediction), 2)
        })

    avg_historical = df['amount'].mean()
    trend_direction = "increasing" if model.coef_[0] > 0 else "decreasing"
    monthly_change = abs(model.coef_[0])

    return {
        "forecast": forecasts,
        "total_year_forecast": round(float(total_forecast), 2),
        "average_monthly_forecast": round(float(total_forecast / 12), 2),
        "historical_monthly_average": round(float(avg_historical), 2),
        "trend": trend_direction,
        "monthly_change_rate": round(float(monthly_change), 2),
        "confidence": round(float(r_squared), 2),
        "based_on_months": len(df)
    }
