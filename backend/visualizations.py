import matplotlib
# Use non-interactive backend for server environments
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import pandas as pd
from sqlalchemy.orm import Session
from backend import analytics

def generate_chart_base64(fig) -> str:
    """Converts a matplotlib figure to a base64 string"""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig) # Free memory
    return img_base64

def create_monthly_trend_chart(db: Session, months: int = 6) -> str:
    trend_data = analytics.get_monthly_spending_trend(db, months)

    fig, ax = plt.subplots(figsize=(10, 6))

    if not trend_data:
        ax.text(0.5, 0.5, 'No data available for trend chart', ha='center', va='center')
    else:
        df = pd.DataFrame(trend_data)
        ax.plot(df['month'], df['amount'], marker='o', linestyle='-', linewidth=2, color='#3498db')
        ax.fill_between(df['month'], df['amount'], alpha=0.2, color='#3498db')
        ax.set_title('Monthly Spending Trend', fontsize=16)
        ax.set_ylabel('Amount ($)')
        ax.grid(True, linestyle='--', alpha=0.7)

    return generate_chart_base64(fig)

def create_category_pie_chart(db: Session, limit: int = 5) -> str:
    data = analytics.get_top_spending_categories(db, limit)

    fig, ax = plt.subplots(figsize=(8, 8))

    if not data:
        ax.text(0.5, 0.5, 'No data available for category chart', ha='center', va='center')
    else:
        df = pd.DataFrame(data)
        colors = ['#ff9999','#66b3ff','#99ff99','#ffcc99', '#c2c2f0']
        ax.pie(df['amount'], labels=df['category'], autopct='%1.1f%%', startangle=90, colors=colors, shadow=True)
        ax.set_title(f'Top {len(df)} Spending Categories', fontsize=16)

    return generate_chart_base64(fig)

def create_budget_comparison_chart(db: Session) -> str:
    # Logic to compare budget vs actual
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.text(0.5, 0.5, 'Budget comparison chart coming soon', ha='center', va='center')
    return generate_chart_base64(fig)

def create_spending_patterns_chart(db: Session) -> str:
    pattern_data = analytics.get_spending_patterns(db)

    fig, ax = plt.subplots(figsize=(10, 6))

    if not pattern_data:
        ax.text(0.5, 0.5, 'No pattern data available', ha='center', va='center')
    else:
        days = list(pattern_data.keys())
        amounts = list(pattern_data.values())
        ax.bar(days, amounts, color='#8e44ad')
        ax.set_title('Total Spending by Day of Week', fontsize=16)
        ax.set_ylabel('Total Amount ($)')

    return generate_chart_base64(fig)

def create_income_expense_chart(db: Session, months: int = 6) -> str:
    # Comparative bar chart for income vs expenses
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.text(0.5, 0.5, 'Income vs Expense chart coming soon', ha='center', va='center')
    return generate_chart_base64(fig)

def create_category_trend_chart(db: Session, category_name: str, months: int = 6) -> str:
    # Trend for a specific category
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_title(f'Trend for {category_name}')
    return generate_chart_base64(fig)
