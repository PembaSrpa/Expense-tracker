from backend.database import engine, Base
from backend.models import Category, Transaction, Budget

def init_database():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ All tables created successfully!")
    print("\nTables created:")
    print("- categories")
    print("- transactions")
    print("- budgets")

if __name__ == "__main__":
    init_database()
