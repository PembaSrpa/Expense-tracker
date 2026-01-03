from dotenv import load_dotenv
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load environment variables from .env file
load_dotenv()

# --- STEP 1: SMART VARIABLE DETECTION (SUPABASE VERSION) ---
# Supabase gives you a full URL, which is much safer than building it manually
DATABASE_URL = os.getenv("DATABASE_URL")

# Fallback: If you are still using individual variables in your .env
if not DATABASE_URL:
    user = os.getenv("DB_USER", "postgres")
    pw = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    # Remember: Use 6543 for Transaction Pooling on Render!
    port = os.getenv("DB_PORT", "6543")
    db_name = os.getenv("DB_NAME", "postgres")

    if host:
        DATABASE_URL = f"postgresql://{user}:{pw}@{host}:{port}/{db_name}"

# --- STEP 2: BUILD & FIX THE URL ---
if DATABASE_URL is None:
    print("CRITICAL ERROR: DATABASE_URL not found. Check your .env or Render Variables.")
else:
    # Ensure it starts with postgresql:// and not mysql
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# --- STEP 3: INITIALIZE ENGINE ---
# We added pooling arguments because Supabase connections can time out on Render
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
