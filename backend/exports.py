import csv
import io
from sqlalchemy.orm import Session
from backend.models import Transaction, Budget
from datetime import date
from typing import Optional

def export_transactions_csv(db: Session,
                            start_date: Optional[date] = None,
                            end_date: Optional[date] = None) -> str:
    """Export transactions to CSV format"""
    # Query transactions
    query = db.query(Transaction)

    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)

    transactions = query.order_by(Transaction.date.desc()).all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(['ID', 'Date', 'Amount', 'Category', 'Description', 'Type', 'Created At'])

    # Write data
    for t in transactions:
        writer.writerow([
            t.id,
            t.date.strftime('%Y-%m-%d'),
            f'{t.amount:.2f}',
            t.category_rel.name,
            t.description or '',
            t.transaction_type.value,
            t.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])

    return output.getvalue()


def export_budgets_csv(db: Session) -> str:
    """Export budgets to CSV format"""
    budgets = db.query(Budget).all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(['ID', 'Category', 'Monthly Limit', 'Start Date', 'Created At'])

    # Write data
    for b in budgets:
        writer.writerow([
            b.id,
            b.category_rel.name,
            f'{b.monthly_limit:.2f}',
            b.start_date.strftime('%Y-%m-%d'),
            b.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])

    return output.getvalue()


def export_summary_csv(db: Session,
                       start_date: Optional[date] = None,
                       end_date: Optional[date] = None) -> str:
    """Export spending summary by category to CSV"""
    from backend.crud import get_spending_by_category, get_total_income_expense
    import io
    import csv

    # Get spending by category and overall totals
    spending = get_spending_by_category(db, start_date, end_date)
    totals = get_total_income_expense(db, start_date, end_date)

    output = io.StringIO()
    writer = csv.writer(output)

    # Summary section
    writer.writerow(['EXPENSE SUMMARY'])
    writer.writerow(['Period', f'{start_date or "All time"} to {end_date or "Present"}'])
    writer.writerow([])

    # Totals - accessing dictionary keys
    writer.writerow(['Total Income', f"${totals['total_income']:.2f}"])
    writer.writerow(['Total Expenses', f"${totals['total_expense']:.2f}"])
    writer.writerow(['Net (Savings)', f"${totals['net']:.2f}"])
    writer.writerow([])

    # By category
    writer.writerow(['Category Breakdown'])
    writer.writerow(['Category', 'Amount', 'Percentage'])

    total_expenses = totals['total_expense']

    # FIX: Use bracket notation [] instead of dot notation .
    for s in spending:
        amount = float(s['total'])
        category_name = s['category']

        percentage = (amount / total_expenses * 100) if total_expenses > 0 else 0
        writer.writerow([category_name, f'${amount:.2f}', f'{percentage:.1f}%'])

    return output.getvalue()
