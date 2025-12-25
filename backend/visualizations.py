import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server
import matplotlib.pyplot as plt
import io
import base64
from sqlalchemy.orm import Session
from backend import analytics, crud
from datetime import date, timedelta
from typing import Optional
import pandas as pd

# Set style
plt.style.use('seaborn-v0_8-darkgrid')

def generate_chart_base64(fig) -> str:
    """Convert matplotlib figure to base64 string"""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return img_base64


# ============= CHART GENERATION FUNCTIONS =============

def create_monthly_trend_chart(db: Session, months: int = 6) -> str:
    """Generate monthly spending trend line chart"""
    trend_data = analytics.get_monthly_spending_trend(db, months)

    if not trend_data:
        # Create empty chart with message
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, 'No data available',
                ha='center', va='center', fontsize=16)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        return generate_chart_base64(fig)

    df = pd.DataFrame(trend_data)

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df['month'], df['amount'], marker='o', linewidth=3,
            markersize=10, color='#3498db', markerfacecolor='#e74c3c')

    ax.set_title('Monthly Spending Trend', fontsize=18, fontweight='bold', pad=20)
    ax.set_xlabel('Month', fontsize=14, fontweight='bold')
    ax.set_ylabel('Amount ($)', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')

    # Rotate x-axis labels
    plt.xticks(rotation=45, ha='right')

    # Add value labels on points
    for i, row in df.iterrows():
        ax.annotate(f'${row["amount"]:.0f}',
                   (i, row['amount']),
                   textcoords="offset points",
                   xytext=(0,10),
                   ha='center',
                   fontsize=10,
                   fontweight='bold')

    plt.tight_layout()
    return generate_chart_base64(fig)


def create_category_pie_chart(db: Session, limit: int = 5) -> str:
    """Generate pie chart for top spending categories"""
    top_cats = analytics.get_top_spending_categories(db, limit)

    if not top_cats:
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.text(0.5, 0.5, 'No data available',
                ha='center', va='center', fontsize=16)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        return generate_chart_base64(fig)

    df = pd.DataFrame(top_cats)

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 10))

    # Custom colors
    colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6',
              '#1abc9c', '#34495e', '#e67e22']

    wedges, texts, autotexts = ax.pie(
        df['amount'],
        labels=df['category'],
        autopct='%1.1f%%',
        startangle=90,
        colors=colors[:len(df)],
        explode=[0.05] * len(df),  # Slightly separate slices
        shadow=True,
        textprops={'fontsize': 12, 'fontweight': 'bold'}
    )

    # Make percentage text white and bold
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(14)

    ax.set_title(f'Top {limit} Spending Categories',
                fontsize=18, fontweight='bold', pad=20)

    plt.tight_layout()
    return generate_chart_base64(fig)


def create_budget_comparison_chart(db: Session) -> str:
    """Generate bar chart comparing budget vs actual spending"""
    budgets = crud.get_budgets(db)

    # Get current month's spending
    today = date.today()
    start_of_month = date(today.year, today.month, 1)
    spending = crud.get_spending_by_category(db, start_of_month, today)

    if not budgets:
        # ... (empty chart logic) ...
        return generate_chart_base64(fig)

    # Prepare data
    categories = [b.category_rel.name for b in budgets]
    budget_amounts = [b.monthly_limit for b in budgets]
    actual_amounts = [
        next((s['total'] for s in spending if s['category'] == b.category_rel.name), 0)
        for b in budgets
    ]

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 7))

    x = range(len(categories))
    width = 0.35

    bars1 = ax.bar([i - width/2 for i in x], budget_amounts, width,
                   label='Budget', alpha=0.8, color='#3498db')
    bars2 = ax.bar([i + width/2 for i in x], actual_amounts, width,
                   label='Actual', alpha=0.8, color='#e74c3c')

    ax.set_xlabel('Category', fontsize=14, fontweight='bold')
    ax.set_ylabel('Amount ($)', fontsize=14, fontweight='bold')
    ax.set_title('Budget vs Actual Spending (Current Month)',
                fontsize=18, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(categories, rotation=45, ha='right')
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3, axis='y', linestyle='--')

    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'${height:.0f}',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3),
                       textcoords="offset points",
                       ha='center', va='bottom',
                       fontsize=10, fontweight='bold')

    plt.tight_layout()
    return generate_chart_base64(fig)


def create_spending_patterns_chart(db: Session) -> str:
    """Generate chart showing spending patterns by day of week"""
    patterns = analytics.get_spending_patterns(db)

    if 'error' in patterns:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, patterns['error'],
                ha='center', va='center', fontsize=16)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        return generate_chart_base64(fig)

    # Get day of week data
    by_day = patterns.get('by_day_of_week', {})

    # Order days properly
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                 'Friday', 'Saturday', 'Sunday']
    days = [day for day in day_order if day in by_day]
    amounts = [by_day[day] for day in days]

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 7))

    # Color weekends differently
    colors = ['#3498db' if day not in ['Saturday', 'Sunday']
              else '#e74c3c' for day in days]

    bars = ax.bar(days, amounts, color=colors, alpha=0.8, edgecolor='black')

    ax.set_xlabel('Day of Week', fontsize=14, fontweight='bold')
    ax.set_ylabel('Total Spending ($)', fontsize=14, fontweight='bold')
    ax.set_title('Spending Pattern by Day of Week',
                fontsize=18, fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3, axis='y', linestyle='--')

    # Rotate labels
    plt.xticks(rotation=45, ha='right')

    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'${height:.0f}',
                   xy=(bar.get_x() + bar.get_width() / 2, height),
                   xytext=(0, 3),
                   textcoords="offset points",
                   ha='center', va='bottom',
                   fontsize=11, fontweight='bold')

    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#3498db', alpha=0.8, label='Weekday'),
        Patch(facecolor='#e74c3c', alpha=0.8, label='Weekend')
    ]
    ax.legend(handles=legend_elements, fontsize=12)

    plt.tight_layout()
    return generate_chart_base64(fig)


def create_income_expense_chart(db: Session, months: int = 6) -> str:
    """Generate chart comparing income vs expenses over time"""
    end_date = date.today()
    start_date = end_date - timedelta(days=months * 30)

    df = analytics.transactions_to_dataframe(db, start_date, end_date)

    if df.empty:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.text(0.5, 0.5, 'No data available',
                ha='center', va='center', fontsize=16)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        return generate_chart_base64(fig)

    # Group by month and type
    df['month'] = df['date'].dt.to_period('M')
    monthly_data = df.groupby(['month', 'type'])['amount'].sum().unstack(fill_value=0)
    monthly_data.index = monthly_data.index.astype(str)

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 7))

    x = range(len(monthly_data))
    width = 0.35

    income = monthly_data.get('income', [0] * len(monthly_data))
    expense = monthly_data.get('expense', [0] * len(monthly_data))

    bars1 = ax.bar([i - width/2 for i in x], income, width,
                   label='Income', alpha=0.8, color='#2ecc71')
    bars2 = ax.bar([i + width/2 for i in x], expense, width,
                   label='Expenses', alpha=0.8, color='#e74c3c')

    ax.set_xlabel('Month', fontsize=14, fontweight='bold')
    ax.set_ylabel('Amount ($)', fontsize=14, fontweight='bold')
    ax.set_title('Income vs Expenses Over Time',
                fontsize=18, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(monthly_data.index, rotation=45, ha='right')
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3, axis='y', linestyle='--')

    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.annotate(f'${height:.0f}',
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3),
                           textcoords="offset points",
                           ha='center', va='bottom',
                           fontsize=10, fontweight='bold')

    plt.tight_layout()
    return generate_chart_base64(fig)


def create_category_trend_chart(db: Session, category: str, months: int = 6) -> str:
    """Generate trend chart for a specific category"""
    trend_data = analytics.get_category_trend(db, category, months)

    if not trend_data:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, f'No data for category: {category}',
                ha='center', va='center', fontsize=16)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        return generate_chart_base64(fig)

    df = pd.DataFrame(trend_data)

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df['month'], df['amount'], marker='o', linewidth=3,
            markersize=10, color='#9b59b6', markerfacecolor='#e74c3c')

    ax.set_title(f'Spending Trend: {category.title()}',
                fontsize=18, fontweight='bold', pad=20)
    ax.set_xlabel('Month', fontsize=14, fontweight='bold')
    ax.set_ylabel('Amount ($)', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')

    plt.xticks(rotation=45, ha='right')

    # Add value labels
    for i, row in df.iterrows():
        ax.annotate(f'${row["amount"]:.0f}',
                   (i, row['amount']),
                   textcoords="offset points",
                   xytext=(0,10),
                   ha='center',
                   fontsize=10,
                   fontweight='bold')

    plt.tight_layout()
    return generate_chart_base64(fig)
