# test_db.py (create in backend/)
from app.database import engine

try:
    connection = engine.connect()
    print("✅ Database connection successful!")
    connection.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")