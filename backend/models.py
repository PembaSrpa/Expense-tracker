from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base # Adjusted import path
from datetime import datetime, timezone
import enum

# 1. ENUM Fix: PostgreSQL requires a 'name' for the ENUM type in the DB
class TransactionType(enum.Enum):
    income = "income"
    expense = "expense"

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    type = Column(String(20), nullable=False)
    # 2. TIMEZONE Fix: Best practice for Supabase/Postgres is timezone-aware
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    transactions = relationship("Transaction", back_populates="category_rel")
    budgets = relationship("Budget", back_populates="category_rel")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    description = Column(String(255))
    # ENUM name is mandatory for Postgres native types
    transaction_type = Column(SQLEnum(TransactionType, name="transaction_type_enum"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    category_rel = relationship("Category", back_populates="transactions")

class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Ensure this stays unique if one category can only have one budget
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False, unique=True)
    monthly_limit = Column(Float, nullable=False)
    start_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    category_rel = relationship("Category", back_populates="budgets")
