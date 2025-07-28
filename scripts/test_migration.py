#!/usr/bin/env python3
"""
Test script to validate migration syntax and structure.
This script tests the migration without requiring a live database connection.
"""

import sys
import os
import importlib.util
from pathlib import Path

def test_migration_syntax():
    """Test that the migration file has valid Python syntax."""
    print("Testing migration syntax...")
    
    # Find the migration file
    migration_dir = Path("alembic/versions")
    migration_files = list(migration_dir.glob("*.py"))
    
    if not migration_files:
        print("❌ No migration files found!")
        return False
    
    migration_file = migration_files[0]  # Get the first (and should be only) migration
    print(f"Found migration: {migration_file}")
    
    try:
        # Load the migration module
        spec = importlib.util.spec_from_file_location("migration", migration_file)
        migration_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration_module)
        
        # Check that required functions exist
        if not hasattr(migration_module, 'upgrade'):
            print("❌ Migration missing 'upgrade' function!")
            return False
            
        if not hasattr(migration_module, 'downgrade'):
            print("❌ Migration missing 'downgrade' function!")
            return False
            
        # Check revision info
        if not hasattr(migration_module, 'revision'):
            print("❌ Migration missing 'revision' identifier!")
            return False
            
        print(f"✅ Migration syntax is valid!")
        print(f"   Revision: {migration_module.revision}")
        print(f"   Down revision: {migration_module.down_revision}")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration syntax error: {e}")
        return False

def test_migration_structure():
    """Test the structure and content of the migration."""
    print("\nTesting migration structure...")
    
    migration_dir = Path("alembic/versions")
    migration_files = list(migration_dir.glob("*.py"))
    migration_file = migration_files[0]
    
    # Read the migration content
    with open(migration_file, 'r') as f:
        content = f.read()
    
    # Check for expected table creations
    expected_tables = [
        'users', 'opportunities', 'market_signals', 'validations',
        'ai_capability_assessments', 'implementation_guides',
        'reputation_events', 'user_badges', 'expertise_verifications',
        'reputation_summaries'
    ]
    
    missing_tables = []
    for table in expected_tables:
        if f"create_table('{table}'" not in content:
            missing_tables.append(table)
    
    if missing_tables:
        print(f"❌ Missing table creations: {missing_tables}")
        return False
    
    # Check for foreign key constraints
    if 'ForeignKeyConstraint' not in content:
        print("❌ No foreign key constraints found!")
        return False
    
    # Check for indexes
    if 'create_index' not in content:
        print("❌ No indexes found!")
        return False
    
    # Check for enum types
    expected_enums = ['userrole', 'opportunitystatus', 'signaltype', 'validationtype']
    for enum_type in expected_enums:
        if enum_type not in content:
            print(f"❌ Missing enum type: {enum_type}")
            return False
    
    print("✅ Migration structure looks good!")
    print(f"   Found {len(expected_tables)} table creations")
    print("   Found foreign key constraints")
    print("   Found indexes")
    print("   Found enum types")
    
    return True

def test_downgrade_completeness():
    """Test that the downgrade function properly reverses the upgrade."""
    print("\nTesting downgrade completeness...")
    
    migration_dir = Path("alembic/versions")
    migration_files = list(migration_dir.glob("*.py"))
    migration_file = migration_files[0]
    
    with open(migration_file, 'r') as f:
        content = f.read()
    
    # Check that downgrade drops all tables
    expected_tables = [
        'users', 'opportunities', 'market_signals', 'validations',
        'ai_capability_assessments', 'implementation_guides',
        'reputation_events', 'user_badges', 'expertise_verifications',
        'reputation_summaries'
    ]
    
    downgrade_section = content.split('def downgrade()')[1]
    
    missing_drops = []
    for table in expected_tables:
        if f"drop_table('{table}')" not in downgrade_section:
            missing_drops.append(table)
    
    if missing_drops:
        print(f"❌ Downgrade missing table drops: {missing_drops}")
        return False
    
    # Check that enum types are dropped
    if 'DROP TYPE IF EXISTS' not in downgrade_section:
        print("❌ Downgrade doesn't drop enum types!")
        return False
    
    print("✅ Downgrade function is complete!")
    print("   All tables are dropped in downgrade")
    print("   Enum types are cleaned up")
    
    return True

def main():
    """Run all migration tests."""
    print("🧪 Testing Database Migration")
    print("=" * 50)
    
    tests = [
        test_migration_syntax,
        test_migration_structure,
        test_downgrade_completeness
    ]
    
    all_passed = True
    for test in tests:
        if not test():
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All migration tests passed!")
        print("\nNext steps:")
        print("1. Start your PostgreSQL database")
        print("2. Run: alembic upgrade head")
        print("3. Test rollback: alembic downgrade base")
        return 0
    else:
        print("❌ Some migration tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())