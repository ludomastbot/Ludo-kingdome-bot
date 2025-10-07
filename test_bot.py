import os
import sys
from database.models import init_db, SessionLocal, User

def test_database():
    """Test database connection and basic operations"""
    try:
        init_db()
        db = SessionLocal()
        
        print("✅ Database initialized successfully!")
        
        # Test if we can create a session
        test_count = db.query(User).count()
        print(f"✅ Database connection test passed! Total users: {test_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_config():
    """Test configuration loading"""
    try:
        from config import config
        print(f"✅ Config loaded - BOT_TOKEN: {'Set' if config.BOT_TOKEN else 'Not Set'}")
        return True
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing Ludo Bot Setup...")
    config_success = test_config()
    db_success = test_database()
    
    if config_success and db_success:
        print("🎉 All tests passed! Bot is ready for development.")
    else:
        print("❌ Some tests failed. Please check the setup.")
