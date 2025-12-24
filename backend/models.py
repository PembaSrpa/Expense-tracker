from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Enum as SQLEnum
from backend.database import Base
from datetime import datetime, timezone
import enum

# Enum for transaction types
class TransactionType(enum.Enum):
    income = "income"
    expense = "expense"

# Category model
class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    type = Column(String(20), nullable=False)  # 'income' or 'expense'
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# Transaction model
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String(100), nullable=False)
    description = Column(String(255))
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# Budget model
class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(100), nullable=False, unique=True)
    monthly_limit = Column(Float, nullable=False)
    start_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
