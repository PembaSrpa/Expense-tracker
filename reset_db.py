from backend.database import engine
from backend.models import Base

def nuke_database():
    print("Connecting to MySQL to drop tables...")
    # This specifically looks at your Base.metadata and drops matching tables
    Base.metadata.drop_all(bind=engine)
    print("All tables dropped. Your next app start will recreate them.")

if __name__ == "__main__":
    confirm = input("This will delete ALL data. Type 'yes' to proceed: ")
    if confirm.lower() == 'yes':
        nuke_database()
