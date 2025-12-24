from dotenv import load_dotenv
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load environment variables from .env file
load_dotenv()

# --- STEP 1: SMART VARIABLE DETECTION ---
# We prioritize Railway names, but fallback to your EXACT local .env names
user = os.getenv("MYSQLUSER") or os.getenv("DB_USER")
pw = os.getenv("MYSQLPASSWORD") or os.getenv("DB_PASSWORD")
host = os.getenv("MYSQLHOST") or os.getenv("DB_HOST")
port = os.getenv("MYSQLPORT") or os.getenv("DB_PORT") or "3306"
db_name = os.getenv("MYSQLDATABASE") or os.getenv("DB_NAME")

# --- STEP 2: BUILD THE URL ---
# We check if we actually have a host. If not, we print a clear error.
if host is None:
    print("CRITICAL ERROR: Database Host not found. Check your .env or Railway Variables.")
    DATABASE_URL = "mysql+pymysql://error_no_host" # This will trigger a clean error
else:
    DATABASE_URL = f"mysql+pymysql://{user}:{pw}@{host}:{port}/{db_name}"

# --- STEP 3: INITIALIZE ENGINE ---
engine = create_engine(
    DATABASE_URL,
    echo=False
)

# Create a SessionLocal class - each instance will be a database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a Base class for our models
Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
