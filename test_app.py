#!/usr/bin/env python3
"""
Simple test script to verify the MES application can import and start.
"""
import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all required modules can be imported."""
    modules_to_test = [
        "app.main",
        "app.database",
        "app.models",
        "app.schemas",
        "app.tasks",
        "app.erp_integration",
        "app.routers.wrp",
        "app.routers.rfid",
        "app.routers.touchpanel",
    ]
    
    print("Testing imports...")
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"✓ {module_name}")
        except ImportError as e:
            print(f"✗ {module_name}: {e}")
            return False
    
    return True

def test_database_config():
    """Test database configuration."""
    try:
        from app.database import settings, local_engine, init_db
        print(f"\nDatabase configuration:")
        print(f"  SQLite path: {settings.SQLITE_PATH}")
        print(f"  Local engine: {local_engine}")
        
        # Try to initialize database
        init_db()
        print("  Database initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Database configuration error: {e}")
        return False

def test_models():
    """Test that models can be defined."""
    try:
        from app.models import Base
        from app.database import local_engine
        
        # Check that Base metadata exists
        print(f"\nModels check:")
        print(f"  Base metadata tables: {list(Base.metadata.tables.keys())}")
        return True
    except Exception as e:
        print(f"✗ Models error: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("MES System Application Test")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Database", test_database_config),
        ("Models", test_models),
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        print(f"\n{name}:")
        if test_func():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ Application is ready to run!")
        print("\nTo start the application:")
        print("  1. docker-compose up -d")
        print("  2. Access the UI at http://localhost:8000")
        print("  3. Login with username/password or RFID")
    else:
        print("✗ Some tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)