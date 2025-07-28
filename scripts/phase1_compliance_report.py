#!/usr/bin/env python3
"""
Phase 1 Compliance Report
Comprehensive verification that Phase 1 implementation adheres to requirements and design.
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_requirements_compliance() -> Dict[str, bool]:
    """Check compliance with requirements document."""
    print("🔍 Checking Requirements Compliance")
    print("=" * 50)
    
    compliance = {}
    
    # Requirement 2: Opportunity Validation Framework
    print("\n📋 Requirement 2: Opportunity Validation Framework")
    
    try:
        from shared.models.validation import ValidationResult, ValidationType
        from shared.models.opportunity import Opportunity, OpportunityStatus
        
        # Check validation types match requirements
        validation_types = [vt.value for vt in ValidationType]
        expected_types = ['market_demand', 'technical_feasibility', 'business_viability', 'competitive_analysis']
        
        has_validation_types = all(vt in validation_types for vt in expected_types)
        print(f"   ✅ Validation types defined: {has_validation_types}")
        
        # Check opportunity status workflow
        opportunity_statuses = [os.value for os in OpportunityStatus]
        has_workflow_statuses = 'validating' in opportunity_statuses and 'validated' in opportunity_statuses
        print(f"   ✅ Validation workflow statuses: {has_workflow_statuses}")
        
        compliance['req_2_validation_framework'] = has_validation_types and has_workflow_statuses
        
    except Exception as e:
        print(f"   ❌ Error checking validation framework: {e}")
        compliance['req_2_validation_framework'] = False
    
    # Requirement 4: Community Engagement Platform
    print("\n👥 Requirement 4: Community Engagement Platform")
    
    try:
        from shared.models.user import User, UserRole
        from shared.models.reputation import ReputationEvent, UserBadge, ExpertiseVerification, ReputationSummary
        
        # Check expert profiles (4.1)
        user_roles = [ur.value for ur in UserRole]
        has_expert_role = 'expert' in user_roles
        print(f"   ✅ Expert profiles supported: {has_expert_role}")
        
        # Check contribution tracking (4.3)
        has_reputation_tracking = True  # ReputationEvent model exists
        print(f"   ✅ Contribution history tracking: {has_reputation_tracking}")
        
        # Check influence weighting (4.4)
        has_influence_weight = hasattr(ReputationSummary, 'influence_weight')
        print(f"   ✅ Influence weight for quality validation: {has_influence_weight}")
        
        # Check badges system (4.5)
        has_badges = True  # UserBadge model exists
        print(f"   ✅ Reputation points and badges: {has_badges}")
        
        compliance['req_4_community_engagement'] = all([
            has_expert_role, has_reputation_tracking, has_influence_weight, has_badges
        ])
        
    except Exception as e:
        print(f"   ❌ Error checking community engagement: {e}")
        compliance['req_4_community_engagement'] = False
    
    return compliance

def check_design_compliance() -> Dict[str, bool]:
    """Check compliance with design document."""
    print("\n🏗️  Checking Design Document Compliance")
    print("=" * 50)
    
    compliance = {}
    
    # Check Core Data Models
    print("\n📊 Core Data Models")
    
    try:
        from shared.models import (
            Opportunity, MarketSignal, ValidationResult, 
            AICapabilityAssessment, ImplementationGuide,
            User, ReputationEvent, UserBadge
        )
        
        # Verify all required models exist
        required_models = {
            'Opportunity': Opportunity,
            'MarketSignal': MarketSignal, 
            'ValidationResult': ValidationResult,
            'AICapabilityAssessment': AICapabilityAssessment,
            'ImplementationGuide': ImplementationGuide,
            'User': User,
            'ReputationEvent': ReputationEvent,
            'UserBadge': UserBadge
        }
        
        models_exist = True
        for model_name, model_class in required_models.items():
            if model_class is not None:
                print(f"   ✅ {model_name} model exists")
            else:
                print(f"   ❌ {model_name} model missing")
                models_exist = False
        
        compliance['design_data_models'] = models_exist
        
    except Exception as e:
        print(f"   ❌ Error checking data models: {e}")
        compliance['design_data_models'] = False
    
    # Check Database Schema
    print("\n🗄️  Database Schema")
    
    try:
        # Check migration file exists and has all tables
        migration_dir = Path("alembic/versions")
        migration_files = list(migration_dir.glob("*.py"))
        
        if migration_files:
            migration_file = migration_files[0]
            with open(migration_file, 'r') as f:
                content = f.read()
            
            expected_tables = [
                'users', 'opportunities', 'market_signals', 'validations',
                'ai_capability_assessments', 'implementation_guides',
                'reputation_events', 'user_badges', 'expertise_verifications',
                'reputation_summaries'
            ]
            
            tables_created = all(f"create_table('{table}'" in content for table in expected_tables)
            print(f"   ✅ All required tables in migration: {tables_created}")
            
            has_foreign_keys = 'ForeignKeyConstraint' in content
            print(f"   ✅ Foreign key relationships: {has_foreign_keys}")
            
            has_indexes = 'create_index' in content
            print(f"   ✅ Database indexes: {has_indexes}")
            
            compliance['design_database_schema'] = tables_created and has_foreign_keys and has_indexes
        else:
            print("   ❌ No migration files found")
            compliance['design_database_schema'] = False
            
    except Exception as e:
        print(f"   ❌ Error checking database schema: {e}")
        compliance['design_database_schema'] = False
    
    return compliance

def check_infrastructure_setup() -> Dict[str, bool]:
    """Check infrastructure and setup compliance."""
    print("\n🏗️  Infrastructure Setup")
    print("=" * 50)
    
    compliance = {}
    
    # Check project structure
    print("\n📁 Project Structure")
    
    required_dirs = [
        'shared', 'shared/models', 'shared/schemas', 'shared/services',
        'api', 'agents', 'data-ingestion', 'ui', 'alembic', 'scripts', 'tests'
    ]
    
    structure_complete = True
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"   ✅ {dir_path}/ exists")
        else:
            print(f"   ❌ {dir_path}/ missing")
            structure_complete = False
    
    compliance['infrastructure_structure'] = structure_complete
    
    # Check configuration files
    print("\n⚙️  Configuration Files")
    
    config_files = [
        'requirements.txt', 'alembic.ini', 'docker-compose.yml', 
        'README.md', 'Makefile'
    ]
    
    config_complete = True
    for config_file in config_files:
        if Path(config_file).exists():
            print(f"   ✅ {config_file} exists")
        else:
            print(f"   ❌ {config_file} missing")
            config_complete = False
    
    compliance['infrastructure_config'] = config_complete
    
    return compliance

def check_testing_framework() -> Dict[str, bool]:
    """Check testing framework setup."""
    print("\n🧪 Testing Framework")
    print("=" * 50)
    
    compliance = {}
    
    # Check test files exist
    test_files = [
        'tests/test_user_model.py',
        'tests/test_opportunity_model.py', 
        'tests/test_validation_model.py',
        'tests/test_reputation.py',
        'scripts/test_migration.py',
        'scripts/test_db_connection.py'
    ]
    
    tests_exist = True
    for test_file in test_files:
        if Path(test_file).exists():
            print(f"   ✅ {test_file} exists")
        else:
            print(f"   ❌ {test_file} missing")
            tests_exist = False
    
    compliance['testing_framework'] = tests_exist
    
    return compliance

def generate_compliance_summary(all_compliance: Dict[str, Dict[str, bool]]) -> None:
    """Generate overall compliance summary."""
    print("\n" + "=" * 60)
    print("📊 PHASE 1 COMPLIANCE SUMMARY")
    print("=" * 60)
    
    total_checks = 0
    passed_checks = 0
    
    for category, checks in all_compliance.items():
        print(f"\n{category.upper().replace('_', ' ')}:")
        for check_name, passed in checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {check_name}: {status}")
            total_checks += 1
            if passed:
                passed_checks += 1
    
    compliance_percentage = (passed_checks / total_checks) * 100
    print(f"\n📈 OVERALL COMPLIANCE: {passed_checks}/{total_checks} ({compliance_percentage:.1f}%)")
    
    if compliance_percentage >= 90:
        print("🎉 EXCELLENT! Phase 1 is highly compliant with requirements and design.")
    elif compliance_percentage >= 75:
        print("✅ GOOD! Phase 1 meets most requirements with minor gaps.")
    elif compliance_percentage >= 50:
        print("⚠️  MODERATE! Phase 1 has significant gaps that need attention.")
    else:
        print("❌ POOR! Phase 1 requires major improvements before proceeding.")
    
    return compliance_percentage >= 75

def main():
    """Run comprehensive Phase 1 compliance check."""
    print("🔍 AI OPPORTUNITY BROWSER - PHASE 1 COMPLIANCE REPORT")
    print("=" * 60)
    print("Verifying that Phase 1 implementation adheres to requirements and design documents.")
    
    all_compliance = {}
    
    # Run all compliance checks
    all_compliance['requirements'] = check_requirements_compliance()
    all_compliance['design'] = check_design_compliance()
    all_compliance['infrastructure'] = check_infrastructure_setup()
    all_compliance['testing'] = check_testing_framework()
    
    # Generate summary
    is_compliant = generate_compliance_summary(all_compliance)
    
    if is_compliant:
        print("\n🚀 READY TO PROCEED TO PHASE 2!")
        print("Phase 1 foundation is solid and compliant.")
        return 0
    else:
        print("\n⚠️  PHASE 1 NEEDS ATTENTION!")
        print("Address compliance gaps before proceeding to Phase 2.")
        return 1

if __name__ == "__main__":
    sys.exit(main())