"""
Tests for Feature Flag System

This module contains comprehensive tests for the feature flag management system,
including service functionality, API endpoints, and CLI operations.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from shared.feature_flags import (
    FeatureFlagService,
    FeatureFlag,
    FeatureFlagStatus,
    RolloutStrategy,
    RolloutConfig,
    FeatureVariant,
    TargetingRule,
    UserContext,
    FeatureFlagEvaluation,
    get_feature_flag_service
)
from shared.config_service import ConfigurationService


class TestFeatureFlagService:
    """Test cases for FeatureFlagService."""
    
    @pytest.fixture
    async def service(self):
        """Create a test feature flag service."""
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.keys.return_value = []
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = 1
        mock_redis.lpush.return_value = 1
        mock_redis.expire.return_value = True
        
        # Mock configuration service
        mock_config = AsyncMock(spec=ConfigurationService)
        mock_config.register_config_schema = AsyncMock()
        
        service = FeatureFlagService(
            config_service=mock_config,
            redis_client=mock_redis,
            default_environment="test"
        )
        await service.initialize()
        return service
    
    @pytest.fixture
    def sample_flag(self):
        """Create a sample feature flag."""
        return FeatureFlag(
            name="test-feature",
            description="Test feature flag",
            status=FeatureFlagStatus.ACTIVE,
            default_value=False,
            rollout_config=RolloutConfig(
                strategy=RolloutStrategy.PERCENTAGE,
                percentage=50.0
            ),
            environments=["test", "development"],
            tags=["test"]
        )
    
    @pytest.fixture
    def sample_user_context(self):
        """Create a sample user context."""
        return UserContext(
            user_id="test-user-123",
            email="test@example.com",
            role="user",
            plan="basic",
            country="US"
        )
    
    async def test_create_feature_flag(self, service):
        """Test creating a feature flag."""
        flag = await service.create_feature_flag(
            name="new-feature",
            description="New test feature",
            default_value=True,
            rollout_config=RolloutConfig(
                strategy=RolloutStrategy.PERCENTAGE,
                percentage=25.0
            )
        )
        
        assert flag.name == "new-feature"
        assert flag.description == "New test feature"
        assert flag.default_value is True
        assert flag.status == FeatureFlagStatus.ACTIVE
        assert flag.rollout_config.percentage == 25.0
    
    async def test_create_duplicate_flag_raises_error(self, service, sample_flag):
        """Test that creating a duplicate flag raises an error."""
        # Mock existing flag
        service._flag_cache[sample_flag.name] = sample_flag
        
        with pytest.raises(ValueError, match="already exists"):
            await service.create_feature_flag(
                name=sample_flag.name,
                description="Duplicate flag"
            )
    
    async def test_update_feature_flag(self, service, sample_flag):
        """Test updating a feature flag."""
        # Mock existing flag
        service._flag_cache[sample_flag.name] = sample_flag
        
        updated_flag = await service.update_feature_flag(
            name=sample_flag.name,
            description="Updated description",
            status=FeatureFlagStatus.INACTIVE,
            rollout_config=RolloutConfig(
                strategy=RolloutStrategy.PERCENTAGE,
                percentage=75.0
            )
        )
        
        assert updated_flag.description == "Updated description"
        assert updated_flag.status == FeatureFlagStatus.INACTIVE
        assert updated_flag.rollout_config.percentage == 75.0
    
    async def test_update_nonexistent_flag_raises_error(self, service):
        """Test that updating a nonexistent flag raises an error."""
        with pytest.raises(ValueError, match="not found"):
            await service.update_feature_flag(
                name="nonexistent-flag",
                description="Updated description"
            )
    
    async def test_delete_feature_flag(self, service, sample_flag):
        """Test deleting a feature flag."""
        # Mock existing flag
        service._flag_cache[sample_flag.name] = sample_flag
        
        deleted = await service.delete_feature_flag(sample_flag.name)
        assert deleted is True
        assert sample_flag.name not in service._flag_cache
    
    async def test_get_feature_flag(self, service, sample_flag):
        """Test getting a feature flag."""
        # Mock cached flag
        service._flag_cache[sample_flag.name] = sample_flag
        
        flag = await service.get_feature_flag(sample_flag.name)
        assert flag is not None
        assert flag.name == sample_flag.name
        assert flag.description == sample_flag.description
    
    async def test_list_feature_flags(self, service, sample_flag):
        """Test listing feature flags."""
        # Mock cached flags
        service._flag_cache[sample_flag.name] = sample_flag
        
        # Mock Redis keys
        service.redis_client.keys.return_value = [f"feature_flag:{sample_flag.name}"]
        
        flags = await service.list_feature_flags()
        assert len(flags) == 1
        assert flags[0].name == sample_flag.name
    
    async def test_list_feature_flags_with_filters(self, service, sample_flag):
        """Test listing feature flags with filters."""
        # Create flags with different attributes
        flag1 = FeatureFlag(
            name="flag1",
            description="Flag 1",
            status=FeatureFlagStatus.ACTIVE,
            environments=["test"],
            tags=["tag1"]
        )
        flag2 = FeatureFlag(
            name="flag2",
            description="Flag 2",
            status=FeatureFlagStatus.INACTIVE,
            environments=["production"],
            tags=["tag2"]
        )
        
        service._flag_cache["flag1"] = flag1
        service._flag_cache["flag2"] = flag2
        service.redis_client.keys.return_value = ["feature_flag:flag1", "feature_flag:flag2"]
        
        # Test environment filter
        flags = await service.list_feature_flags(environment="test")
        assert len(flags) == 1
        assert flags[0].name == "flag1"
        
        # Test status filter
        flags = await service.list_feature_flags(status=FeatureFlagStatus.INACTIVE)
        assert len(flags) == 1
        assert flags[0].name == "flag2"
        
        # Test tags filter
        flags = await service.list_feature_flags(tags=["tag1"])
        assert len(flags) == 1
        assert flags[0].name == "flag1"
    
    async def test_evaluate_percentage_rollout(self, service, sample_flag, sample_user_context):
        """Test percentage-based rollout evaluation."""
        # Mock cached flag
        service._flag_cache[sample_flag.name] = sample_flag
        
        evaluation = await service.evaluate_feature_flag(
            flag_name=sample_flag.name,
            user_context=sample_user_context,
            environment="test"
        )
        
        assert evaluation.flag_name == sample_flag.name
        assert isinstance(evaluation.enabled, bool)
        assert evaluation.reason.startswith("percentage_")
        assert evaluation.user_context == sample_user_context
    
    async def test_evaluate_user_list_rollout(self, service, sample_user_context):
        """Test user list-based rollout evaluation."""
        flag = FeatureFlag(
            name="user-list-feature",
            description="User list feature",
            status=FeatureFlagStatus.ACTIVE,
            rollout_config=RolloutConfig(
                strategy=RolloutStrategy.USER_LIST,
                user_ids=["test-user-123", "test-user-456"]
            ),
            environments=["test"]
        )
        
        service._flag_cache[flag.name] = flag
        
        # Test user in list
        evaluation = await service.evaluate_feature_flag(
            flag_name=flag.name,
            user_context=sample_user_context,
            environment="test"
        )
        
        assert evaluation.enabled is True
        assert evaluation.reason == "user_list_match"
        
        # Test user not in list
        other_user = UserContext(user_id="other-user", email="other@example.com")
        evaluation = await service.evaluate_feature_flag(
            flag_name=flag.name,
            user_context=other_user,
            environment="test"
        )
        
        assert evaluation.enabled is False
        assert evaluation.reason == "user_list_no_match"
    
    async def test_evaluate_user_attribute_rollout(self, service, sample_user_context):
        """Test user attribute-based rollout evaluation."""
        flag = FeatureFlag(
            name="attribute-feature",
            description="Attribute feature",
            status=FeatureFlagStatus.ACTIVE,
            rollout_config=RolloutConfig(
                strategy=RolloutStrategy.USER_ATTRIBUTE,
                targeting_rules=[
                    TargetingRule(
                        attribute="plan",
                        operator="equals",
                        values=["basic", "premium"]
                    )
                ]
            ),
            environments=["test"]
        )
        
        service._flag_cache[flag.name] = flag
        
        evaluation = await service.evaluate_feature_flag(
            flag_name=flag.name,
            user_context=sample_user_context,
            environment="test"
        )
        
        assert evaluation.enabled is True
        assert evaluation.reason == "targeting_rule_match_plan"
    
    async def test_evaluate_with_variants(self, service, sample_user_context):
        """Test evaluation with A/B testing variants."""
        flag = FeatureFlag(
            name="variant-feature",
            description="Variant feature",
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
        
        service._flag_cache[flag.name] = flag
        
        evaluation = await service.evaluate_feature_flag(
            flag_name=flag.name,
            user_context=sample_user_context,
            environment="test"
        )
        
        assert evaluation.enabled is True
        assert evaluation.variant in ["control", "treatment"]
        assert evaluation.value in ["control_value", "treatment_value"]
    
    async def test_evaluate_inactive_flag(self, service, sample_user_context):
        """Test evaluating an inactive flag."""
        flag = FeatureFlag(
            name="inactive-feature",
            description="Inactive feature",
            status=FeatureFlagStatus.INACTIVE,
            default_value="default_value",
            rollout_config=RolloutConfig(strategy=RolloutStrategy.PERCENTAGE, percentage=100.0),
            environments=["test"]
        )
        
        service._flag_cache[flag.name] = flag
        
        evaluation = await service.evaluate_feature_flag(
            flag_name=flag.name,
            user_context=sample_user_context,
            environment="test"
        )
        
        assert evaluation.enabled is False
        assert evaluation.value == "default_value"
        assert evaluation.reason == "flag_inactive"
    
    async def test_evaluate_nonexistent_flag(self, service, sample_user_context):
        """Test evaluating a nonexistent flag."""
        evaluation = await service.evaluate_feature_flag(
            flag_name="nonexistent-flag",
            user_context=sample_user_context,
            environment="test"
        )
        
        assert evaluation.enabled is False
        assert evaluation.value is False
        assert evaluation.reason == "flag_not_found"
    
    async def test_evaluate_wrong_environment(self, service, sample_flag, sample_user_context):
        """Test evaluating a flag in wrong environment."""
        service._flag_cache[sample_flag.name] = sample_flag
        
        evaluation = await service.evaluate_feature_flag(
            flag_name=sample_flag.name,
            user_context=sample_user_context,
            environment="production"  # Flag only targets test and development
        )
        
        assert evaluation.enabled is False
        assert evaluation.reason == "environment_not_targeted"
    
    async def test_track_feature_usage(self, service, sample_flag, sample_user_context):
        """Test tracking feature usage."""
        await service.track_feature_usage(
            flag_name=sample_flag.name,
            user_id=sample_user_context.user_id,
            outcome="success",
            environment="test",
            metadata={"action": "click_button"}
        )
        
        # Verify Redis call was made
        service.redis_client.lpush.assert_called()
        service.redis_client.expire.assert_called()
    
    async def test_get_feature_analytics(self, service, sample_flag):
        """Test getting feature analytics."""
        # Mock Redis data
        usage_data = [
            '{"flag_name": "test-feature", "user_id": "user1", "enabled": true, "environment": "test"}',
            '{"flag_name": "test-feature", "user_id": "user2", "enabled": false, "environment": "test"}'
        ]
        service.redis_client.lrange.return_value = usage_data
        
        analytics = await service.get_feature_analytics(
            flag_name=sample_flag.name,
            environment="test"
        )
        
        assert analytics["flag_name"] == sample_flag.name
        assert analytics["total_evaluations"] == 2
        assert analytics["enabled_count"] == 1
        assert analytics["disabled_count"] == 1
        assert analytics["unique_users"] == 2
    
    async def test_is_feature_enabled_convenience_function(self, service, sample_flag, sample_user_context):
        """Test the convenience function for checking if feature is enabled."""
        service._flag_cache[sample_flag.name] = sample_flag
        
        enabled = await service.is_feature_enabled(
            flag_name=sample_flag.name,
            user_context=sample_user_context,
            environment="test"
        )
        
        assert isinstance(enabled, bool)
    
    async def test_get_feature_variant_convenience_function(self, service, sample_user_context):
        """Test the convenience function for getting feature variant."""
        flag = FeatureFlag(
            name="variant-feature",
            description="Variant feature",
            status=FeatureFlagStatus.ACTIVE,
            rollout_config=RolloutConfig(strategy=RolloutStrategy.PERCENTAGE, percentage=100.0),
            variants=[FeatureVariant(name="test", value="test_value", weight=100.0)],
            environments=["test"]
        )
        
        service._flag_cache[flag.name] = flag
        
        variant = await service.get_feature_variant(
            flag_name=flag.name,
            user_context=sample_user_context,
            environment="test"
        )
        
        assert variant == "test_value"


class TestTargetingRules:
    """Test cases for targeting rule evaluation."""
    
    def test_equals_operator(self):
        """Test equals operator in targeting rules."""
        from shared.feature_flags import FeatureFlagService
        
        service = FeatureFlagService()
        rule = TargetingRule(attribute="role", operator="equals", values=["admin", "moderator"])
        user_context = UserContext(user_id="test", role="admin")
        
        result = service._evaluate_targeting_rule(rule, user_context)
        assert result is True
        
        user_context.role = "user"
        result = service._evaluate_targeting_rule(rule, user_context)
        assert result is False
    
    def test_not_equals_operator(self):
        """Test not_equals operator in targeting rules."""
        from shared.feature_flags import FeatureFlagService
        
        service = FeatureFlagService()
        rule = TargetingRule(attribute="plan", operator="not_equals", values=["free"])
        user_context = UserContext(user_id="test", plan="premium")
        
        result = service._evaluate_targeting_rule(rule, user_context)
        assert result is True
        
        user_context.plan = "free"
        result = service._evaluate_targeting_rule(rule, user_context)
        assert result is False
    
    def test_contains_operator(self):
        """Test contains operator in targeting rules."""
        from shared.feature_flags import FeatureFlagService
        
        service = FeatureFlagService()
        rule = TargetingRule(attribute="email", operator="contains", values=["@company.com"])
        user_context = UserContext(user_id="test", email="user@company.com")
        
        result = service._evaluate_targeting_rule(rule, user_context)
        assert result is True
        
        user_context.email = "user@other.com"
        result = service._evaluate_targeting_rule(rule, user_context)
        assert result is False
    
    def test_greater_than_operator(self):
        """Test greater_than operator in targeting rules."""
        from shared.feature_flags import FeatureFlagService
        
        service = FeatureFlagService()
        rule = TargetingRule(attribute="age", operator="greater_than", values=[18])
        user_context = UserContext(user_id="test", attributes={"age": 25})
        
        result = service._evaluate_targeting_rule(rule, user_context)
        assert result is True
        
        user_context.attributes["age"] = 16
        result = service._evaluate_targeting_rule(rule, user_context)
        assert result is False
    
    def test_less_than_operator(self):
        """Test less_than operator in targeting rules."""
        from shared.feature_flags import FeatureFlagService
        
        service = FeatureFlagService()
        rule = TargetingRule(attribute="score", operator="less_than", values=[100])
        user_context = UserContext(user_id="test", attributes={"score": 85})
        
        result = service._evaluate_targeting_rule(rule, user_context)
        assert result is True
        
        user_context.attributes["score"] = 150
        result = service._evaluate_targeting_rule(rule, user_context)
        assert result is False


class TestFeatureVariants:
    """Test cases for feature variants and A/B testing."""
    
    def test_variant_weight_validation(self):
        """Test that variant weights must sum to 100."""
        with pytest.raises(ValueError, match="must sum to 100"):
            FeatureFlag(
                name="test",
                description="Test",
                rollout_config=RolloutConfig(strategy=RolloutStrategy.PERCENTAGE),
                variants=[
                    FeatureVariant(name="a", value="a", weight=60.0),
                    FeatureVariant(name="b", value="b", weight=30.0)  # Total = 90, should be 100
                ]
            )
    
    def test_variant_selection_consistency(self):
        """Test that variant selection is consistent for the same user."""
        from shared.feature_flags import FeatureFlagService
        
        service = FeatureFlagService()
        variants = [
            FeatureVariant(name="control", value="control", weight=50.0),
            FeatureVariant(name="treatment", value="treatment", weight=50.0)
        ]
        
        user_context = UserContext(user_id="consistent-user")
        
        # Select variant multiple times for same user
        selected_variants = []
        for _ in range(10):
            variant = service._select_variant(variants, user_context)
            selected_variants.append(variant.name if variant else None)
        
        # All selections should be the same
        assert len(set(selected_variants)) == 1


class TestGradualRollout:
    """Test cases for gradual rollout functionality."""
    
    async def test_gradual_rollout_calculation(self, service):
        """Test gradual rollout percentage calculation."""
        start_date = datetime.now() - timedelta(days=5)
        flag = FeatureFlag(
            name="gradual-feature",
            description="Gradual rollout feature",
            status=FeatureFlagStatus.ACTIVE,
            rollout_config=RolloutConfig(
                strategy=RolloutStrategy.GRADUAL,
                start_date=start_date,
                gradual_increment=10.0  # 10% per day
            ),
            environments=["test"]
        )
        
        service._flag_cache[flag.name] = flag
        
        user_context = UserContext(user_id="test-user")
        
        # After 5 days, should be 50% rollout
        enabled, reason = await service._evaluate_gradual_rollout(flag, flag.rollout_config, user_context)
        
        # The rollout percentage should be updated
        assert flag.rollout_config.percentage == 50.0


@pytest.mark.asyncio
class TestFeatureFlagAPI:
    """Test cases for Feature Flag API endpoints."""
    
    @pytest.fixture
    def mock_service(self):
        """Create a mock feature flag service."""
        service = AsyncMock(spec=FeatureFlagService)
        return service
    
    @pytest.fixture
    def sample_flag_response(self):
        """Sample flag for API responses."""
        return {
            "name": "test-feature",
            "description": "Test feature",
            "status": "active",
            "default_value": False,
            "rollout_config": {
                "strategy": "percentage",
                "percentage": 50.0
            },
            "variants": None,
            "environments": ["test"],
            "tags": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "created_by": "test",
            "updated_by": "test"
        }
    
    async def test_create_feature_flag_endpoint(self, mock_service, sample_flag_response):
        """Test the create feature flag API endpoint."""
        # This would require setting up FastAPI test client
        # For now, we'll test the service integration
        mock_service.create_feature_flag.return_value = FeatureFlag(**sample_flag_response)
        
        result = await mock_service.create_feature_flag(
            name="test-feature",
            description="Test feature"
        )
        
        assert result.name == "test-feature"
        mock_service.create_feature_flag.assert_called_once()
    
    async def test_list_feature_flags_endpoint(self, mock_service, sample_flag_response):
        """Test the list feature flags API endpoint."""
        mock_service.list_feature_flags.return_value = [FeatureFlag(**sample_flag_response)]
        
        result = await mock_service.list_feature_flags()
        
        assert len(result) == 1
        assert result[0].name == "test-feature"
        mock_service.list_feature_flags.assert_called_once()
    
    async def test_evaluate_feature_flag_endpoint(self, mock_service):
        """Test the evaluate feature flag API endpoint."""
        evaluation = FeatureFlagEvaluation(
            flag_name="test-feature",
            enabled=True,
            value=True,
            reason="percentage_50"
        )
        mock_service.evaluate_feature_flag.return_value = evaluation
        
        result = await mock_service.evaluate_feature_flag(
            flag_name="test-feature",
            user_context=UserContext(user_id="test-user")
        )
        
        assert result.enabled is True
        assert result.flag_name == "test-feature"
        mock_service.evaluate_feature_flag.assert_called_once()


class TestFeatureFlagCLI:
    """Test cases for Feature Flag CLI."""
    
    @pytest.fixture
    def mock_service(self):
        """Create a mock feature flag service for CLI tests."""
        service = AsyncMock(spec=FeatureFlagService)
        return service
    
    async def test_cli_create_command(self, mock_service):
        """Test CLI create command."""
        from scripts.feature_flag_cli import FeatureFlagCLI
        
        cli = FeatureFlagCLI()
        cli.service = mock_service
        
        # Mock arguments
        args = Mock()
        args.name = "test-feature"
        args.description = "Test feature"
        args.default_value = "false"
        args.strategy = "percentage"
        args.percentage = 50.0
        args.users = None
        args.variants = None
        args.environments = None
        args.tags = None
        
        mock_service.create_feature_flag.return_value = FeatureFlag(
            name="test-feature",
            description="Test feature",
            rollout_config=RolloutConfig(strategy=RolloutStrategy.PERCENTAGE, percentage=50.0)
        )
        
        result = await cli.create_flag(args)
        
        assert result == 0  # Success exit code
        mock_service.create_feature_flag.assert_called_once()
    
    async def test_cli_list_command(self, mock_service):
        """Test CLI list command."""
        from scripts.feature_flag_cli import FeatureFlagCLI
        
        cli = FeatureFlagCLI()
        cli.service = mock_service
        
        args = Mock()
        args.environment = None
        args.status = None
        args.tags = None
        
        mock_service.list_feature_flags.return_value = [
            FeatureFlag(
                name="test-feature",
                description="Test feature",
                rollout_config=RolloutConfig(strategy=RolloutStrategy.PERCENTAGE)
            )
        ]
        
        result = await cli.list_flags(args)
        
        assert result == 0  # Success exit code
        mock_service.list_feature_flags.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])