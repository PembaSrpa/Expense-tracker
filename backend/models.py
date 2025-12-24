from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
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

    # Relationships
    transactions = relationship("Transaction", back_populates="category_rel")
    budgets = relationship("Budget", back_populates="category_rel")

# Transaction model
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    description = Column(String(255))
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship
    category_rel = relationship("Category", back_populates="transactions")

# Budget model
class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False, unique=True)
    monthly_limit = Column(Float, nullable=False)
    start_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship
    category_rel = relationship("Category", back_populates="budgets")
