from sqlalchemy.orm import Session
from backend.models import Transaction, Budget, Category, TransactionType
from datetime import datetime, date
from typing import Optional, List

# ============= TRANSACTION OPERATIONS =============

def create_transaction(db: Session, date: date, amount: float, category_id: int,
                      description: str, transaction_type: TransactionType):
    """Create a new transaction"""
    # Create a new Transaction object with the provided data
    db_transaction = Transaction(
        date=date,
        amount=amount,
        category_id=category_id,
        description=description,
        transaction_type=transaction_type
    )
    # Add it to the session (staging area)
    db.add(db_transaction)
    # Save changes to database
    db.commit()
    # Refresh to get the auto-generated ID from database
    db.refresh(db_transaction)
    return db_transaction


def get_transactions(db: Session, skip: int = 0, limit: int = 100,
                     category_id: Optional[int] = None,
                     start_date: Optional[date] = None,
                     end_date: Optional[date] = None,
                     transaction_type: Optional[TransactionType] = None):
    """Get all transactions with optional filters"""
    # Start a query on the Transaction table
    query = db.query(Transaction)

    # Apply filters if provided
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)

    # Order by date (newest first) and apply pagination
    return query.order_by(Transaction.date.desc()).offset(skip).limit(limit).all()


def get_transaction_by_id(db: Session, transaction_id: int):
    """Get a specific transaction by ID"""
    # Query and return the first match (or None if not found)
    return db.query(Transaction).filter(Transaction.id == transaction_id).first()


def update_transaction(db: Session, transaction_id: int,
                      date: Optional[date] = None,
                      amount: Optional[float] = None,
                      category_id: Optional[int] = None,
                      description: Optional[str] = None,
                      transaction_type: Optional[TransactionType] = None):
    """Update a transaction"""
    # Find the transaction
    db_transaction = get_transaction_by_id(db, transaction_id)

    if not db_transaction:
        return None

    # Update only the fields that were provided
    if date:
        db_transaction.date = date
    if amount is not None:  # Check 'is not None' because amount could be 0
        db_transaction.amount = amount
    if category_id:
        db_transaction.category_id = category_id
    if description is not None:  # Description could be empty string
        db_transaction.description = description
    if transaction_type:
        db_transaction.transaction_type = transaction_type

    # Save changes
    db.commit()
    db.refresh(db_transaction)
    return db_transaction


def delete_transaction(db: Session, transaction_id: int):
    """Delete a transaction"""
    # Find the transaction
    db_transaction = get_transaction_by_id(db, transaction_id)

    if not db_transaction:
        return False

    # Delete it
    db.delete(db_transaction)
    db.commit()
    return True


# ============= BUDGET OPERATIONS =============

def create_budget(db: Session, category_id: int, monthly_limit: float, start_date: date):
    """Create a new budget for a category"""
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
    """Get all budgets"""
    return db.query(Budget).all()


def get_budget_by_category_id(db: Session, category_id: int):
    """Get budget for a specific category"""
    return db.query(Budget).filter(Budget.category_id == category_id).first()


def update_budget(db: Session, budget_id: int,
                 monthly_limit: Optional[float] = None,
                 start_date: Optional[date] = None):
    """Update a budget"""
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
    """Delete a budget"""
    db_budget = db.query(Budget).filter(Budget.id == budget_id).first()

    if not db_budget:
        return False

    db.delete(db_budget)
    db.commit()
    return True


# ============= CATEGORY OPERATIONS =============

def create_category(db: Session, name: str, type: str):
    """Create a new category"""
    db_category = Category(
        name=name,
        type=type
    )
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


def get_categories(db: Session, type: Optional[str] = None):
    """Get all categories, optionally filtered by type"""
    query = db.query(Category)

    if type:
        query = query.filter(Category.type == type)

    return query.all()

def get_category_by_id(db: Session, category_id: int):  # NEW
    """Get a specific category by ID"""
    return db.query(Category).filter(Category.id == category_id).first()

def get_category_by_name(db: Session, name: str):
    """Get a specific category by name"""
    return db.query(Category).filter(Category.name == name).first()


# ============= ANALYTICS OPERATIONS =============

def get_spending_by_category(db: Session, start_date: Optional[date] = None,
                             end_date: Optional[date] = None):
    """Get total spending grouped by category"""
    from sqlalchemy import func

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

    return [type('obj', (object,), {'category': r[0], 'total': r[1]})() for r in results]


def get_total_income_expense(db: Session, start_date: Optional[date] = None,
                             end_date: Optional[date] = None):
    """Get total income and expenses"""
    from sqlalchemy import func

    # Get total income
    income_query = db.query(func.sum(Transaction.amount)).filter(
        Transaction.transaction_type == TransactionType.income
    )

    # Get total expenses
    expense_query = db.query(func.sum(Transaction.amount)).filter(
        Transaction.transaction_type == TransactionType.expense
    )

    # Apply date filters
    if start_date:
        income_query = income_query.filter(Transaction.date >= start_date)
        expense_query = expense_query.filter(Transaction.date >= start_date)
    if end_date:
        income_query = income_query.filter(Transaction.date <= end_date)
        expense_query = expense_query.filter(Transaction.date <= end_date)

    total_income = income_query.scalar() or 0
    total_expense = expense_query.scalar() or 0

    return {
        'total_income': total_income,
        'total_expense': total_expense,
        'net': total_income - total_expense
    }


def get_budget_vs_actual(db: Session, category_id: int, start_date: date, end_date: date):  # CHANGED
    """Compare budget to actual spending for a category"""
    from sqlalchemy import func

    # Get the budget
    budget = get_budget_by_category_id(db, category_id)

    # Get category name
    category = get_category_by_id(db, category_id)
    category_name = category.name if category else "Unknown"

    # Get actual spending
    actual = db.query(func.sum(Transaction.amount)).filter(
        Transaction.category_id == category_id,
        Transaction.transaction_type == TransactionType.expense,
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).scalar() or 0

    budget_amount = budget.monthly_limit if budget else 0

    return {
        'category': category_name,
        'budget': budget_amount,
        'actual': actual,
        'remaining': budget_amount - actual,
        'percentage_used': (actual / budget_amount * 100) if budget_amount > 0 else 0
    }
