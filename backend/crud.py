from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from backend.models import Transaction, Budget, Category, TransactionType
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from typing import Optional, List

def create_transaction(db: Session, date: date, amount: float, category_id: int,
                       description: str, transaction_type: TransactionType):
    db_transaction = Transaction(
        date=date,
        amount=amount,
        category_id=category_id,
        description=description,
        transaction_type=transaction_type
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

def get_transactions(db: Session, skip: int = 0, limit: int = 100,
                     category_id: Optional[int] = None,
                     start_date: Optional[date] = None,
                     end_date: Optional[date] = None,
                     transaction_type: Optional[TransactionType] = None):
    query = db.query(Transaction).options(joinedload(Transaction.category_rel))

    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)

    transactions = query.order_by(Transaction.date.desc()).offset(skip).limit(limit).all()

    for txn in transactions:
        if not hasattr(txn, "category_name"):
            txn.category_name = txn.category_rel.name if txn.category_rel else "Uncategorized"

    return transactions

def get_transaction_by_id(db: Session, transaction_id: int):
    transaction = db.query(Transaction)\
        .options(joinedload(Transaction.category_rel))\
        .filter(Transaction.id == transaction_id)\
        .first()

    if not transaction:
        return None

    if not hasattr(transaction, "category_name"):
        transaction.category_name = transaction.category_rel.name if transaction.category_rel else "Uncategorized"

    return transaction

def update_transaction(db: Session, transaction_id: int,
                       date: Optional[date] = None,
                       amount: Optional[float] = None,
                       category_id: Optional[int] = None,
                       description: Optional[str] = None,
                       transaction_type: Optional[TransactionType] = None):
    db_transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()

    if not db_transaction:
        return None

    if date:
        db_transaction.date = date
    if amount is not None:
        db_transaction.amount = amount
    if category_id:
        db_transaction.category_id = category_id
    if description is not None:
        db_transaction.description = description
    if transaction_type:
        db_transaction.transaction_type = transaction_type

    db.commit()
    db.refresh(db_transaction)

    db_transaction.category_name = db_transaction.category_rel.name if db_transaction.category_rel else "Uncategorized"

    return db_transaction

def delete_transaction(db: Session, transaction_id: int):
    db_transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()

    if not db_transaction:
        return False

    db.delete(db_transaction)
    db.commit()
    return True

def create_budget(db: Session, category_id: int, monthly_limit: float, start_date: date):
    db_budget = Budget(
        category_id=category_id,
        monthly_limit=monthly_limit,
        start_date=start_date
    )
    db.add(db_budget)
    db.commit()
    db.refresh(db_budget)
    return db_budget

def get_budgets(db: Session):
    budgets = db.query(Budget).options(joinedload(Budget.category_rel)).all()
    return budgets

def get_budget_by_category_id(db: Session, category_id: int):
    return db.query(Budget).filter(Budget.category_id == category_id).first()

def update_budget(db: Session, budget_id: int,
                  monthly_limit: Optional[float] = None,
                  start_date: Optional[date] = None):
    db_budget = db.query(Budget).filter(Budget.id == budget_id).first()

    if not db_budget:
        return None

    if monthly_limit is not None:
        db_budget.monthly_limit = monthly_limit
    if start_date:
        db_budget.start_date = start_date

    db.commit()
    db.refresh(db_budget)
    return db_budget

def delete_budget(db: Session, budget_id: int):
    db_budget = db.query(Budget).filter(Budget.id == budget_id).first()

    if not db_budget:
        return False

    db.delete(db_budget)
    db.commit()
    return True

def create_category(db: Session, name: str, type: str):
    db_category = Category(
        name=name,
        type=type
    )
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

def get_categories(db: Session, type: Optional[str] = None):
    query = db.query(Category)
    if type:
        query = query.filter(Category.type == type)
    return query.all()

def get_category_by_id(db: Session, category_id: int):
    return db.query(Category).filter(Category.id == category_id).first()

def get_category_by_name(db: Session, name: str):
    return db.query(Category).filter(Category.name == name).first()

def get_spending_by_category(db: Session, start_date: Optional[date] = None,
                             end_date: Optional[date] = None):
    query = db.query(
        Category.name,
        func.sum(Transaction.amount).label('total')
    ).join(Transaction, Transaction.category_id == Category.id)\
     .filter(Transaction.transaction_type == TransactionType.expense)

    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)

    results = query.group_by(Category.name).all()

    return [{'category': r[0], 'total': float(r[1])} for r in results]

def get_total_income_expense(db: Session, start_date: Optional[date] = None,
                             end_date: Optional[date] = None):
    income_query = db.query(func.sum(Transaction.amount)).filter(
        Transaction.transaction_type == TransactionType.income
    )

    expense_query = db.query(func.sum(Transaction.amount)).filter(
        Transaction.transaction_type == TransactionType.expense
    )

    if start_date:
        income_query = income_query.filter(Transaction.date >= start_date)
        expense_query = expense_query.filter(Transaction.date >= start_date)
    if end_date:
        income_query = income_query.filter(Transaction.date <= end_date)
        expense_query = expense_query.filter(Transaction.date <= end_date)

    total_income = income_query.scalar() or 0
    total_expense = expense_query.scalar() or 0

    return {
        'total_income': float(total_income),
        'total_expense': float(total_expense),
        'net': float(total_income - total_expense)
    }

def get_budget_vs_actual(db: Session, category_id: int, start_date: date, end_date: date):
    budget = get_budget_by_category_id(db, category_id)
    category = get_category_by_id(db, category_id)
    category_name = category.name if category else "Unknown"

    actual = db.query(func.sum(Transaction.amount)).filter(
        Transaction.category_id == category_id,
        Transaction.transaction_type == TransactionType.expense,
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).scalar() or 0

    budget_amount = float(budget.monthly_limit) if budget else 0.0
    actual_float = float(actual)

    return {
        'category': category_name,
        'budget': budget_amount,
        'actual': actual_float,
        'remaining': budget_amount - actual_float,
        'percentage_used': (actual_float / budget_amount * 100) if budget_amount > 0 else 0
    }
