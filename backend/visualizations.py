import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import pandas as pd
from sqlalchemy.orm import Session
from backend import analytics

def generate_chart_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return img_base64

def create_monthly_trend_chart(db: Session, months: int = 6) -> str:
    trend_data = analytics.get_monthly_spending_trend(db, months)
    fig, ax = plt.subplots(figsize=(10, 6))
    if not trend_data:
        ax.text(0.5, 0.5, 'No Data', ha='center')
        return generate_chart_base64(fig)
    df = pd.DataFrame(trend_data)
    ax.plot(df['month'], df['amount'], marker='o')
    ax.set_title('Spending Trend')
    return generate_chart_base64(fig)

def create_category_pie_chart(db: Session, limit: int = 5) -> str:
    data = analytics.get_top_spending_categories(db, limit)
    fig, ax = plt.subplots(figsize=(8, 8))
    if not data:
        ax.text(0.5, 0.5, 'No Data', ha='center')
        return generate_chart_base64(fig)
    df = pd.DataFrame(data)
    ax.pie(df['amount'], labels=df['category'], autopct='%1.1f%%')
    return generate_chart_base64(fig)
