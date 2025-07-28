#!/usr/bin/env python3
"""
Feature Flag System Demo

This script demonstrates the feature flag management system capabilities:
- Creating feature flags with different rollout strategies
- Evaluating flags for different user contexts
- A/B testing with variants
- Analytics and usage tracking
- Gradual rollout scenarios
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from typing import List

# Add the project root to the path
sys.path.append('.')

from shared.feature_flags import (
    FeatureFlagService,
    FeatureFlagStatus,
    RolloutStrategy,
    RolloutConfig,
    FeatureVariant,
    TargetingRule,
    UserContext
)


class FeatureFlagDemo:
    """Demonstration of feature flag system capabilities."""
    
    def __init__(self):
        self.service: FeatureFlagService = None
    
    async def initialize(self):
        """Initialize the feature flag service."""
        print("🚀 Initializing Feature Flag System...")
        self.service = FeatureFlagService(enable_analytics=True)
        await self.service.initialize()
        print("✅ Feature Flag System initialized\n")
    
    async def demo_basic_feature_flags(self):
        """Demonstrate basic feature flag operations."""
        print("=" * 60)
        print("📋 BASIC FEATURE FLAG OPERATIONS")
        print("=" * 60)
        
        # Create a simple feature flag
        print("1. Creating a simple feature flag...")
        flag = await self.service.create_feature_flag(
            name="new-dashboard",
            description="Enable the new dashboard UI",
            default_value=False,
            rollout_config=RolloutConfig(
                strategy=RolloutStrategy.PERCENTAGE,
                percentage=0.0  # Start disabled
            ),
            environments=["development", "staging", "production"],
            tags=["ui", "dashboard"],
            created_by="demo"
        )
        print(f"   ✅ Created flag: {flag.name}")
        print(f"   📝 Description: {flag.description}")
        print(f"   🎯 Strategy: {flag.rollout_config.strategy.value}")
        print(f"   📊 Percentage: {flag.rollout_config.percentage}%")
        
        # List all flags
        print("\n2. Listing all feature flags...")
        flags = await self.service.list_feature_flags()
        print(f"   📋 Found {len(flags)} feature flag(s):")
        for f in flags:
            print(f"      - {f.name}: {f.status.value} ({f.rollout_config.strategy.value})")
        
        # Update the flag to enable it
        print("\n3. Enabling the feature flag...")
        await self.service.update_feature_flag(
            name="new-dashboard",
            rollout_config=RolloutConfig(
                strategy=RolloutStrategy.PERCENTAGE,
                percentage=100.0
            ),
            updated_by="demo"
        )
        print("   ✅ Feature flag enabled at 100%")
        
        print()
    
    async def demo_rollout_strategies(self):
        """Demonstrate different rollout strategies."""
        print("=" * 60)
        print("🎯 ROLLOUT STRATEGIES")
        print("=" * 60)
        
        # Percentage rollout
        print("1. Percentage-based rollout...")
        await self.service.create_feature_flag(
            name="percentage-feature",
            description="Feature with percentage rollout",
            rollout_config=RolloutConfig(
                strategy=RolloutStrategy.PERCENTAGE,
                percentage=25.0
            ),
            created_by="demo"
        )
        print("   ✅ Created feature with 25% rollout")
        
        # User list rollout
        print("\n2. User list-based rollout...")
        await self.service.create_feature_flag(
            name="beta-users-feature",
            description="Feature for beta users only",
            rollout_config=RolloutConfig(
                strategy=RolloutStrategy.USER_LIST,
                user_ids=["beta-user-1", "beta-user-2", "beta-user-3"]
            ),
            created_by="demo"
        )
        print("   ✅ Created feature for specific beta users")
        
        # User attribute rollout
        print("\n3. User attribute-based rollout...")
        await self.service.create_feature_flag(
            name="premium-feature",
            description="Feature for premium users",
            rollout_config=RolloutConfig(
                strategy=RolloutStrategy.USER_ATTRIBUTE,
                targeting_rules=[
                    TargetingRule(
                        attribute="plan",
                        operator="equals",
                        values=["premium", "enterprise"]
                    )
                ]
            ),
            created_by="demo"
        )
        print("   ✅ Created feature for premium users")
        
        # Gradual rollout
        print("\n4. Gradual rollout...")
        await self.service.create_feature_flag(
            name="gradual-feature",
            description="Feature with gradual rollout",
            rollout_config=RolloutConfig(
                strategy=RolloutStrategy.GRADUAL,
                start_date=datetime.now(),
                gradual_increment=20.0  # 20% per day
            ),
            created_by="demo"
        )
        print("   ✅ Created feature with gradual rollout (20% per day)")
        
        print()
    
    async def demo_ab_testing(self):
        """Demonstrate A/B testing with variants."""
        print("=" * 60)
        print("🧪 A/B TESTING WITH VARIANTS")
        print("=" * 60)
        
        # Create feature with variants
        print("1. Creating A/B test feature...")
        await self.service.create_feature_flag(
            name="checkout-button-test",
            description="A/B test for checkout button design",
            rollout_config=RolloutConfig(
                strategy=RolloutStrategy.PERCENTAGE,
                percentage=100.0
            ),
            variants=[
                FeatureVariant(
                    name="control",
                    value={"color": "blue", "text": "Buy Now"},
                    weight=50.0,
                    description="Original blue button"
                ),
                FeatureVariant(
                    name="treatment",
                    value={"color": "green", "text": "Purchase"},
                    weight=50.0,
                    description="New green button"
                )
            ],
            created_by="demo"
        )
        print("   ✅ Created A/B test with 50/50 split")
        
        # Test variant assignment for different users
        print("\n2. Testing variant assignment...")
        test_users = [
            UserContext(user_id=f"user-{i}", email=f"user{i}@example.com")
            for i in range(1, 11)
        ]
        
        variant_counts = {"control": 0, "treatment": 0}
        
        for user in test_users:
            evaluation = await self.service.evaluate_feature_flag(
                flag_name="checkout-button-test",
                user_context=user
            )
            if evaluation.variant:
                variant_counts[evaluation.variant] += 1
                print(f"   👤 {user.user_id}: {evaluation.variant} -> {evaluation.value}")
        
        print(f"\n   📊 Variant distribution:")
        print(f"      Control: {variant_counts['control']} users")
        print(f"      Treatment: {variant_counts['treatment']} users")
        
        print()
    
    async def demo_user_targeting(self):
        """Demonstrate user targeting and evaluation."""
        print("=" * 60)
        print("👥 USER TARGETING AND EVALUATION")
        print("=" * 60)
        
        # Create different user contexts
        users = [
            UserContext(
                user_id="user-1",
                email="basic@example.com",
                role="user",
                plan="basic",
                country="US"
            ),
            UserContext(
                user_id="user-2",
                email="premium@example.com",
                role="user",
                plan="premium",
                country="US"
            ),
            UserContext(
                user_id="admin-1",
                email="admin@example.com",
                role="admin",
                plan="enterprise",
                country="CA"
            ),
            UserContext(
                user_id="beta-user-1",
                email="beta@example.com",
                role="user",
                plan="basic",
                country="UK"
            )
        ]
        
        # Test different flags against different users
        test_flags = [
            "percentage-feature",
            "beta-users-feature",
            "premium-feature"
        ]
        
        print("Evaluating flags for different users:")
        print()
        
        for user in users:
            print(f"👤 User: {user.user_id} ({user.plan} plan, {user.role} role)")
            
            for flag_name in test_flags:
                try:
                    evaluation = await self.service.evaluate_feature_flag(
                        flag_name=flag_name,
                        user_context=user
                    )
                    
                    status = "✅ ENABLED" if evaluation.enabled else "❌ DISABLED"
                    print(f"   🏁 {flag_name}: {status} ({evaluation.reason})")
                    
                except Exception as e:
                    print(f"   ❌ {flag_name}: Error - {e}")
            
            print()
    
    async def demo_analytics_tracking(self):
        """Demonstrate analytics and usage tracking."""
        print("=" * 60)
        print("📊 ANALYTICS AND USAGE TRACKING")
        print("=" * 60)
        
        # Simulate usage tracking
        print("1. Simulating feature usage...")
        
        # Track usage for different outcomes
        outcomes = ["success", "conversion", "error", "timeout"]
        users = [f"user-{i}" for i in range(1, 21)]
        
        for i, user_id in enumerate(users):
            outcome = outcomes[i % len(outcomes)]
            await self.service.track_feature_usage(
                flag_name="new-dashboard",
                user_id=user_id,
                outcome=outcome,
                metadata={"session_id": f"session-{i}", "page": "dashboard"}
            )
        
        print(f"   ✅ Tracked usage for {len(users)} users")
        
        # Get analytics
        print("\n2. Retrieving analytics...")
        try:
            analytics = await self.service.get_feature_analytics(
                flag_name="new-dashboard",
                start_date=datetime.now() - timedelta(days=1),
                end_date=datetime.now()
            )
            
            if analytics:
                print(f"   📈 Analytics for 'new-dashboard':")
                print(f"      Total evaluations: {analytics.get('total_evaluations', 0)}")
                print(f"      Enabled count: {analytics.get('enabled_count', 0)}")
                print(f"      Disabled count: {analytics.get('disabled_count', 0)}")
                print(f"      Unique users: {analytics.get('unique_users', 0)}")
            else:
                print("   ℹ️  No analytics data available yet")
        
        except Exception as e:
            print(f"   ⚠️  Analytics not available: {e}")
        
        print()
    
    async def demo_advanced_scenarios(self):
        """Demonstrate advanced feature flag scenarios."""
        print("=" * 60)
        print("🚀 ADVANCED SCENARIOS")
        print("=" * 60)
        
        # Multi-environment feature
        print("1. Multi-environment feature flag...")
        await self.service.create_feature_flag(
            name="multi-env-feature",
            description="Feature with different environments",
            rollout_config=RolloutConfig(
                strategy=RolloutStrategy.PERCENTAGE,
                percentage=100.0
            ),
            environments=["development", "staging"],  # Not in production
            created_by="demo"
        )
        
        # Test in different environments
        user = UserContext(user_id="test-user", email="test@example.com")
        
        for env in ["development", "staging", "production"]:
            evaluation = await self.service.evaluate_feature_flag(
                flag_name="multi-env-feature",
                user_context=user,
                environment=env
            )
            status = "✅ ENABLED" if evaluation.enabled else "❌ DISABLED"
            print(f"   🌍 {env}: {status} ({evaluation.reason})")
        
        # Complex targeting rules
        print("\n2. Complex targeting rules...")
        await self.service.create_feature_flag(
            name="complex-targeting",
            description="Feature with complex targeting",
            rollout_config=RolloutConfig(
                strategy=RolloutStrategy.USER_ATTRIBUTE,
                targeting_rules=[
                    TargetingRule(
                        attribute="country",
                        operator="in",
                        values=["US", "CA", "UK"]
                    ),
                    TargetingRule(
                        attribute="plan",
                        operator="not_equals",
                        values=["free"]
                    )
                ]
            ),
            created_by="demo"
        )
        
        # Test complex targeting
        test_users = [
            UserContext(user_id="us-premium", country="US", plan="premium"),
            UserContext(user_id="uk-basic", country="UK", plan="basic"),
            UserContext(user_id="de-premium", country="DE", plan="premium"),
            UserContext(user_id="us-free", country="US", plan="free")
        ]
        
        print("   Testing complex targeting:")
        for user in test_users:
            evaluation = await self.service.evaluate_feature_flag(
                flag_name="complex-targeting",
                user_context=user
            )
            status = "✅ ENABLED" if evaluation.enabled else "❌ DISABLED"
            print(f"      {user.user_id} ({user.country}, {user.plan}): {status}")
        
        print()
    
    async def demo_flag_management(self):
        """Demonstrate flag lifecycle management."""
        print("=" * 60)
        print("🔄 FLAG LIFECYCLE MANAGEMENT")
        print("=" * 60)
        
        # Create a temporary flag
        print("1. Creating temporary feature flag...")
        await self.service.create_feature_flag(
            name="temp-feature",
            description="Temporary feature for demo",
            rollout_config=RolloutConfig(
                strategy=RolloutStrategy.PERCENTAGE,
                percentage=50.0
            ),
            created_by="demo"
        )
        print("   ✅ Created temporary flag")
        
        # Update the flag
        print("\n2. Updating flag status...")
        await self.service.update_feature_flag(
            name="temp-feature",
            status=FeatureFlagStatus.INACTIVE,
            updated_by="demo"
        )
        print("   ✅ Flag deactivated")
        
        # Archive the flag
        print("\n3. Archiving flag...")
        await self.service.update_feature_flag(
            name="temp-feature",
            status=FeatureFlagStatus.ARCHIVED,
            updated_by="demo"
        )
        print("   ✅ Flag archived")
        
        # Clean up - delete the flag
        print("\n4. Cleaning up...")
        deleted = await self.service.delete_feature_flag("temp-feature", deleted_by="demo")
        if deleted:
            print("   ✅ Temporary flag deleted")
        else:
            print("   ⚠️  Flag not found for deletion")
        
        print()
    
    async def demo_bulk_operations(self):
        """Demonstrate bulk operations."""
        print("=" * 60)
        print("📦 BULK OPERATIONS")
        print("=" * 60)
        
        # Create multiple flags for bulk testing
        bulk_flags = [
            ("bulk-feature-1", "First bulk feature"),
            ("bulk-feature-2", "Second bulk feature"),
            ("bulk-feature-3", "Third bulk feature")
        ]
        
        print("1. Creating multiple flags...")
        for name, description in bulk_flags:
            await self.service.create_feature_flag(
                name=name,
                description=description,
                rollout_config=RolloutConfig(
                    strategy=RolloutStrategy.PERCENTAGE,
                    percentage=0.0
                ),
                created_by="demo"
            )
        print(f"   ✅ Created {len(bulk_flags)} flags")
        
        # Bulk evaluation
        print("\n2. Bulk evaluation for user...")
        user = UserContext(user_id="bulk-test-user", email="bulk@example.com")
        
        results = {}
        for name, _ in bulk_flags:
            evaluation = await self.service.evaluate_feature_flag(
                flag_name=name,
                user_context=user
            )
            results[name] = evaluation.enabled
        
        print("   📋 Bulk evaluation results:")
        for flag_name, enabled in results.items():
            status = "✅ ENABLED" if enabled else "❌ DISABLED"
            print(f"      {flag_name}: {status}")
        
        # Clean up bulk flags
        print("\n3. Cleaning up bulk flags...")
        for name, _ in bulk_flags:
            await self.service.delete_feature_flag(name, deleted_by="demo")
        print("   ✅ Bulk flags cleaned up")
        
        print()
    
    async def run_demo(self):
        """Run the complete feature flag demo."""
        print("🎯 FEATURE FLAG SYSTEM DEMONSTRATION")
        print("=" * 60)
        print("This demo showcases the comprehensive feature flag management system")
        print("with gradual rollout capabilities, A/B testing, and analytics.")
        print()
        
        try:
            await self.initialize()
            
            # Run all demo sections
            await self.demo_basic_feature_flags()
            await self.demo_rollout_strategies()
            await self.demo_ab_testing()
            await self.demo_user_targeting()
            await self.demo_analytics_tracking()
            await self.demo_advanced_scenarios()
            await self.demo_flag_management()
            await self.demo_bulk_operations()
            
            # Final summary
            print("=" * 60)
            print("📋 DEMO SUMMARY")
            print("=" * 60)
            
            flags = await self.service.list_feature_flags()
            print(f"Total feature flags created: {len(flags)}")
            
            active_flags = [f for f in flags if f.status == FeatureFlagStatus.ACTIVE]
            print(f"Active flags: {len(active_flags)}")
            
            if active_flags:
                print("\nActive flags:")
                for flag in active_flags:
                    print(f"  - {flag.name}: {flag.rollout_config.strategy.value}")
                    if flag.rollout_config.percentage is not None:
                        print(f"    Rollout: {flag.rollout_config.percentage}%")
            
            print("\n✅ Feature Flag System Demo completed successfully!")
            print("\nKey capabilities demonstrated:")
            print("  🎯 Multiple rollout strategies (percentage, user list, attributes, gradual)")
            print("  🧪 A/B testing with weighted variants")
            print("  👥 Advanced user targeting and segmentation")
            print("  📊 Usage analytics and tracking")
            print("  🌍 Multi-environment support")
            print("  🔄 Complete flag lifecycle management")
            print("  📦 Bulk operations and management")
            
        except Exception as e:
            print(f"❌ Demo failed with error: {e}")
            import traceback
            traceback.print_exc()
            return 1
        
        return 0


async def main():
    """Main demo function."""
    demo = FeatureFlagDemo()
    return await demo.run_demo()


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Demo interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)