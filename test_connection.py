from dotenv import load_dotenv
import os
import pymysql

load_dotenv()

try:
    connection = pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
    print("✅ MySQL connection successful!")
    connection.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")
