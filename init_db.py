from backend.database import engine, SessionLocal
from backend import models, crud

def init():
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    existing = crud.get_categories(db)
    if not existing:
        categories = [
            ("Food", "expense"),
            ("Rent", "expense"),
            ("Salary", "income"),
            ("Utilities", "expense"),
            ("Freelance", "income")
        ]
        for name, cat_type in categories:
            crud.create_category(db, name=name, type=cat_type)
        db.commit()
    db.close()

if __name__ == "__main__":
    init()
