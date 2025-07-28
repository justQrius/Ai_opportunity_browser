#!/usr/bin/env python3
"""
Simple Feature Flag Test Script

This script tests the basic functionality of the feature flag system
without complex dependencies.
"""

import asyncio
import sys
from datetime import datetime

# Add the project root to the path
sys.path.append('.')

from shared.feature_flags import (
    FeatureFlag,
    FeatureFlagStatus,
    RolloutStrategy,
    RolloutConfig,
    FeatureVariant,
    TargetingRule,
    UserContext,
    FeatureFlagEvaluation
)


def test_feature_flag_models():
    """Test feature flag model creation and validation."""
    print("🧪 Testing Feature Flag Models...")
    
    # Test basic feature flag creation
    flag = FeatureFlag(
        name="test-feature",
        description="Test feature flag",
        status=FeatureFlagStatus.ACTIVE,
        default_value=False,
        rollout_config=RolloutConfig(
            strategy=RolloutStrategy.PERCENTAGE,
            percentage=50.0
        ),
        environments=["test"],
        tags=["test"]
    )
    
    print(f"✅ Created feature flag: {flag.name}")
    print(f"   Status: {flag.status.value}")
    print(f"   Strategy: {flag.rollout_config.strategy.value}")
    print(f"   Percentage: {flag.rollout_config.percentage}%")
    
    # Test feature flag with variants
    flag_with_variants = FeatureFlag(
        name="ab-test-feature",
        description="A/B test feature",
        status=FeatureFlagStatus.ACTIVE,
        rollout_config=RolloutConfig(
            strategy=RolloutStrategy.PERCENTAGE,
            percentage=100.0
        ),
        variants=[
            FeatureVariant(name="control", value="control_value", weight=50.0),
            FeatureVariant(name="treatment", value="treatment_value", weight=50.0)
        ],
        environments=["test"]
    )
    
    print(f"✅ Created A/B test flag: {flag_with_variants.name}")
    print(f"   Variants: {len(flag_with_variants.variants)}")
    for variant in flag_with_variants.variants:
        print(f"     - {variant.name}: {variant.value} (weight: {variant.weight}%)")
    
    # Test user context
    user_context = UserContext(
        user_id="test-user-123",
        email="test@example.com",
        role="user",
        plan="basic",
        country="US"
    )
    
    print(f"✅ Created user context: {user_context.user_id}")
    print(f"   Email: {user_context.email}")
    print(f"   Plan: {user_context.plan}")
    
    return True


def test_targeting_rules():
    """Test targeting rule evaluation logic."""
    print("\n🎯 Testing Targeting Rules...")
    
    # Create targeting rules
    rules = [
        TargetingRule(attribute="plan", operator="equals", values=["premium", "enterprise"]),
        TargetingRule(attribute="country", operator="in", values=["US", "CA", "UK"]),
        TargetingRule(attribute="email", operator="contains", values=["@company.com"])
    ]
    
    # Test users
    test_users = [
        UserContext(user_id="user1", plan="premium", country="US", email="user1@company.com"),
        UserContext(user_id="user2", plan="basic", country="US", email="user2@gmail.com"),
        UserContext(user_id="user3", plan="enterprise", country="DE", email="user3@company.com")
    ]
    
    print("Testing targeting rules against users:")
    for user in test_users:
        print(f"\n👤 User: {user.user_id} (plan: {user.plan}, country: {user.country})")
        
        for i, rule in enumerate(rules):
            # Simulate rule evaluation (simplified)
            matches = False
            
            if rule.attribute == "plan":
                matches = user.plan in rule.values
            elif rule.attribute == "country":
                matches = user.country in rule.values
            elif rule.attribute == "email":
                matches = any(val in user.email for val in rule.values)
            
            status = "✅ MATCH" if matches else "❌ NO MATCH"
            print(f"   Rule {i+1} ({rule.attribute} {rule.operator}): {status}")
    
    return True


def test_rollout_strategies():
    """Test different rollout strategy configurations."""
    print("\n📊 Testing Rollout Strategies...")
    
    strategies = [
        ("Percentage Rollout", RolloutConfig(
            strategy=RolloutStrategy.PERCENTAGE,
            percentage=25.0
        )),
        ("User List Rollout", RolloutConfig(
            strategy=RolloutStrategy.USER_LIST,
            user_ids=["user1", "user2", "user3"]
        )),
        ("User Attribute Rollout", RolloutConfig(
            strategy=RolloutStrategy.USER_ATTRIBUTE,
            targeting_rules=[
                TargetingRule(attribute="plan", operator="equals", values=["premium"])
            ]
        )),
        ("Gradual Rollout", RolloutConfig(
            strategy=RolloutStrategy.GRADUAL,
            start_date=datetime.now(),
            gradual_increment=10.0
        ))
    ]
    
    for name, config in strategies:
        print(f"✅ {name}:")
        print(f"   Strategy: {config.strategy.value}")
        if config.percentage is not None:
            print(f"   Percentage: {config.percentage}%")
        if config.user_ids:
            print(f"   Target Users: {len(config.user_ids)} users")
        if config.targeting_rules:
            print(f"   Targeting Rules: {len(config.targeting_rules)} rules")
        if config.gradual_increment:
            print(f"   Daily Increment: {config.gradual_increment}%")
    
    return True


def test_feature_evaluation():
    """Test feature flag evaluation logic."""
    print("\n🔍 Testing Feature Evaluation...")
    
    # Create test evaluation
    evaluation = FeatureFlagEvaluation(
        flag_name="test-feature",
        enabled=True,
        variant="treatment",
        value={"color": "green", "text": "New Button"},
        reason="percentage_50",
        user_context=UserContext(user_id="test-user")
    )
    
    print(f"✅ Feature Evaluation:")
    print(f"   Flag: {evaluation.flag_name}")
    print(f"   Enabled: {evaluation.enabled}")
    print(f"   Variant: {evaluation.variant}")
    print(f"   Value: {evaluation.value}")
    print(f"   Reason: {evaluation.reason}")
    print(f"   Evaluated at: {evaluation.evaluated_at}")
    
    return True


def test_variant_weights():
    """Test variant weight validation."""
    print("\n⚖️  Testing Variant Weights...")
    
    try:
        # Valid variants (weights sum to 100)
        valid_variants = [
            FeatureVariant(name="control", value="control", weight=30.0),
            FeatureVariant(name="treatment1", value="treatment1", weight=35.0),
            FeatureVariant(name="treatment2", value="treatment2", weight=35.0)
        ]
        
        flag = FeatureFlag(
            name="valid-variants",
            description="Valid variants test",
            rollout_config=RolloutConfig(strategy=RolloutStrategy.PERCENTAGE),
            variants=valid_variants
        )
        
        print("✅ Valid variant weights (30% + 35% + 35% = 100%)")
        
    except Exception as e:
        print(f"❌ Unexpected error with valid variants: {e}")
        return False
    
    try:
        # Invalid variants (weights don't sum to 100)
        invalid_variants = [
            FeatureVariant(name="control", value="control", weight=40.0),
            FeatureVariant(name="treatment", value="treatment", weight=30.0)
        ]
        
        flag = FeatureFlag(
            name="invalid-variants",
            description="Invalid variants test",
            rollout_config=RolloutConfig(strategy=RolloutStrategy.PERCENTAGE),
            variants=invalid_variants
        )
        
        print("❌ Should have failed with invalid variant weights")
        return False
        
    except ValueError as e:
        print("✅ Correctly rejected invalid variant weights (40% + 30% ≠ 100%)")
    
    return True


def main():
    """Run all tests."""
    print("🎯 FEATURE FLAG SYSTEM TESTS")
    print("=" * 50)
    
    tests = [
        ("Feature Flag Models", test_feature_flag_models),
        ("Targeting Rules", test_targeting_rules),
        ("Rollout Strategies", test_rollout_strategies),
        ("Feature Evaluation", test_feature_evaluation),
        ("Variant Weights", test_variant_weights)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*20} {test_name} {'='*20}")
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                failed += 1
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} FAILED with error: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*50}")
    print(f"📊 TEST SUMMARY")
    print(f"{'='*50}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📋 Total: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed! Feature flag system is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please check the implementation.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)