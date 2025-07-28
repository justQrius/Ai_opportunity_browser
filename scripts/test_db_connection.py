#!/usr/bin/env python3
"""
Test database connection and migration application.
This script tests the actual database connection and migration execution.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
import subprocess

def get_database_url():
    """Get database URL from environment or default."""
    return os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ai_opportunity_browser")

def test_database_connection():
    """Test basic database connectivity."""
    print("Testing database connection...")
    
    database_url = get_database_url()
    print(f"Database URL: {database_url}")
    
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Database connection successful!")
            print(f"   PostgreSQL version: {version}")
            return True
    except OperationalError as e:
        print(f"❌ Database connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure PostgreSQL is running")
        print("2. Check database credentials")
        print("3. Verify database exists")
        print("4. Check network connectivity")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_migration_upgrade():
    """Test applying the migration."""
    print("\nTesting migration upgrade...")
    
    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ Migration upgrade successful!")
            print("   All tables created successfully")
            return True
        else:
            print(f"❌ Migration upgrade failed!")
            print(f"   Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Migration upgrade timed out!")
        return False
    except Exception as e:
        print(f"❌ Migration upgrade error: {e}")
        return False

def test_migration_downgrade():
    """Test rolling back the migration."""
    print("\nTesting migration downgrade...")
    
    try:
        result = subprocess.run(
            ["alembic", "downgrade", "base"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ Migration downgrade successful!")
            print("   All tables dropped successfully")
            return True
        else:
            print(f"❌ Migration downgrade failed!")
            print(f"   Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Migration downgrade timed out!")
        return False
    except Exception as e:
        print(f"❌ Migration downgrade error: {e}")
        return False

def test_table_existence():
    """Test that tables were created correctly."""
    print("\nTesting table existence...")
    
    database_url = get_database_url()
    expected_tables = [
        'users', 'opportunities', 'market_signals', 'validations',
        'ai_capability_assessments', 'implementation_guides',
        'reputation_events', 'user_badges', 'expertise_verifications',
        'reputation_summaries'
    ]
    
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            # Check if tables exist
            for table in expected_tables:
                result = conn.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = '{table}'
                    )
                """))
                exists = result.fetchone()[0]
                if not exists:
                    print(f"❌ Table '{table}' does not exist!")
                    return False
            
            print(f"✅ All {len(expected_tables)} tables exist!")
            return True
            
    except Exception as e:
        print(f"❌ Error checking tables: {e}")
        return False

def main():
    """Run all database tests."""
    print("🗄️  Testing Database Migration with Live Database")
    print("=" * 60)
    
    # Test database connection first
    if not test_database_connection():
        print("\n❌ Cannot proceed without database connection")
        print("\nTo set up the database:")
        print("1. Install PostgreSQL")
        print("2. Create database: createdb ai_opportunity_browser")
        print("3. Set DATABASE_URL environment variable (optional)")
        return 1
    
    # Test migration upgrade
    if not test_migration_upgrade():
        print("\n❌ Migration upgrade failed")
        return 1
    
    # Test that tables were created
    if not test_table_existence():
        print("\n❌ Tables were not created properly")
        return 1
    
    # Test migration downgrade
    if not test_migration_downgrade():
        print("\n❌ Migration downgrade failed")
        return 1
    
    # Re-apply migration for final state
    print("\nRe-applying migration for final state...")
    if not test_migration_upgrade():
        print("\n❌ Final migration application failed")
        return 1
    
    print("\n" + "=" * 60)
    print("🎉 All database migration tests passed!")
    print("\nDatabase is ready for development!")
    return 0

if __name__ == "__main__":
    sys.exit(main())