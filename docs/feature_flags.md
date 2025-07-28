# Feature Flag Management System

The AI Opportunity Browser includes a comprehensive feature flag management system that enables gradual rollouts, A/B testing, and dynamic feature control without deployments.

## Overview

The feature flag system provides:

- **Feature Toggle Management**: Enable/disable features dynamically
- **Gradual Rollout Capabilities**: Roll out features to a percentage of users over time
- **A/B Testing Support**: Test multiple variants with weighted distribution
- **User Segmentation**: Target specific users or user groups
- **Analytics and Tracking**: Monitor feature usage and performance
- **Multi-Environment Support**: Different configurations per environment

## Core Components

### 1. Feature Flag Service (`shared/feature_flags.py`)

The main service class that handles all feature flag operations:

```python
from shared.feature_flags import FeatureFlagService, get_feature_flag_service

# Get the service instance
service = await get_feature_flag_service()

# Check if a feature is enabled
enabled = await service.is_feature_enabled("new-dashboard", user_context)

# Get feature variant value
variant = await service.get_feature_variant("checkout-test", user_context)
```

### 2. API Endpoints (`api/routers/feature_flags.py`)

REST API endpoints for managing feature flags:

- `POST /api/v1/feature-flags` - Create a feature flag
- `GET /api/v1/feature-flags` - List feature flags
- `GET /api/v1/feature-flags/{name}` - Get specific flag
- `PUT /api/v1/feature-flags/{name}` - Update a flag
- `DELETE /api/v1/feature-flags/{name}` - Delete a flag
- `POST /api/v1/feature-flags/evaluate` - Evaluate a flag for a user
- `GET /api/v1/feature-flags/{name}/analytics` - Get usage analytics

### 3. CLI Tool (`scripts/feature_flag_cli.py`)

Command-line interface for feature flag management:

```bash
# Create a feature flag
python scripts/feature_flag_cli.py create --name my-feature --description "My feature"

# List all flags
python scripts/feature_flag_cli.py list

# Enable a flag with 50% rollout
python scripts/feature_flag_cli.py enable --name my-feature --percentage 50

# Get analytics
python scripts/feature_flag_cli.py analytics --name my-feature --days 7
```

## Rollout Strategies

### 1. Percentage Rollout

Roll out to a percentage of users:

```python
rollout_config = RolloutConfig(
    strategy=RolloutStrategy.PERCENTAGE,
    percentage=25.0  # 25% of users
)
```

### 2. User List Rollout

Target specific users:

```python
rollout_config = RolloutConfig(
    strategy=RolloutStrategy.USER_LIST,
    user_ids=["user1", "user2", "user3"]
)
```

### 3. User Attribute Rollout

Target users based on attributes:

```python
rollout_config = RolloutConfig(
    strategy=RolloutStrategy.USER_ATTRIBUTE,
    targeting_rules=[
        TargetingRule(
            attribute="plan",
            operator="equals",
            values=["premium", "enterprise"]
        )
    ]
)
```

### 4. Gradual Rollout

Automatically increase rollout percentage over time:

```python
rollout_config = RolloutConfig(
    strategy=RolloutStrategy.GRADUAL,
    start_date=datetime.now(),
    gradual_increment=10.0  # Increase by 10% per day
)
```

## A/B Testing with Variants

Create feature flags with multiple variants for A/B testing:

```python
await service.create_feature_flag(
    name="checkout-button-test",
    description="A/B test for checkout button",
    rollout_config=RolloutConfig(
        strategy=RolloutStrategy.PERCENTAGE,
        percentage=100.0
    ),
    variants=[
        FeatureVariant(
            name="control",
            value={"color": "blue", "text": "Buy Now"},
            weight=50.0
        ),
        FeatureVariant(
            name="treatment",
            value={"color": "green", "text": "Purchase"},
            weight=50.0
        )
    ]
)
```

## User Context

Provide user context for feature evaluation:

```python
user_context = UserContext(
    user_id="user-123",
    email="user@example.com",
    role="user",
    plan="premium",
    country="US",
    attributes={"age": 25, "signup_date": "2024-01-01"}
)

evaluation = await service.evaluate_feature_flag(
    flag_name="premium-feature",
    user_context=user_context
)
```

## Targeting Rules

Define complex targeting rules:

```python
targeting_rules = [
    # Users in specific countries
    TargetingRule(
        attribute="country",
        operator="in",
        values=["US", "CA", "UK"]
    ),
    # Users with company email
    TargetingRule(
        attribute="email",
        operator="contains",
        values=["@company.com"]
    ),
    # Users with high engagement score
    TargetingRule(
        attribute="engagement_score",
        operator="greater_than",
        values=[80]
    )
]
```

### Supported Operators

- `equals` / `not_equals`: Exact match
- `in` / `not_in`: Value in list
- `contains`: String contains substring
- `greater_than` / `less_than`: Numeric comparison

## Analytics and Tracking

Track feature usage and get analytics:

```python
# Track feature usage outcome
await service.track_feature_usage(
    flag_name="new-dashboard",
    user_id="user-123",
    outcome="conversion",
    metadata={"page": "checkout", "amount": 99.99}
)

# Get analytics
analytics = await service.get_feature_analytics(
    flag_name="new-dashboard",
    start_date=datetime.now() - timedelta(days=7),
    end_date=datetime.now()
)

print(f"Total evaluations: {analytics['total_evaluations']}")
print(f"Conversion rate: {analytics['enabled_count'] / analytics['total_evaluations'] * 100:.1f}%")
```

## Environment Management

Configure different settings per environment:

```python
await service.create_feature_flag(
    name="beta-feature",
    description="Beta feature",
    environments=["development", "staging"],  # Not in production
    rollout_config=RolloutConfig(
        strategy=RolloutStrategy.PERCENTAGE,
        percentage=100.0
    )
)
```

## Integration Examples

### In Application Code

```python
from shared.feature_flags import is_feature_enabled, get_feature_variant

async def render_dashboard(user_context):
    # Check if new dashboard is enabled
    if await is_feature_enabled("new-dashboard", user_context):
        return render_new_dashboard()
    else:
        return render_old_dashboard()

async def render_checkout_button(user_context):
    # Get A/B test variant
    variant = await get_feature_variant("checkout-button-test", user_context)
    
    if isinstance(variant, dict):
        return f'<button style="background-color: {variant["color"]}">{variant["text"]}</button>'
    else:
        return '<button>Buy Now</button>'  # Default
```

### In API Endpoints

```python
from fastapi import Depends
from shared.feature_flags import get_feature_flag_service

@router.get("/dashboard")
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    flag_service: FeatureFlagService = Depends(get_feature_flag_service)
):
    user_context = UserContext(
        user_id=current_user.id,
        email=current_user.email,
        plan=current_user.plan
    )
    
    # Check feature flags
    new_ui_enabled = await flag_service.is_feature_enabled("new-ui", user_context)
    advanced_features = await flag_service.is_feature_enabled("advanced-features", user_context)
    
    return {
        "new_ui": new_ui_enabled,
        "advanced_features": advanced_features,
        "user_id": current_user.id
    }
```

## Best Practices

### 1. Naming Conventions

- Use kebab-case for flag names: `new-dashboard`, `checkout-optimization`
- Include the feature area: `auth-sso-login`, `payment-crypto-support`
- Be descriptive: `mobile-responsive-tables` vs `mobile-fix`

### 2. Flag Lifecycle

1. **Development**: Create flag with 0% rollout
2. **Testing**: Enable for specific test users
3. **Gradual Rollout**: Increase percentage over time
4. **Full Rollout**: 100% enabled
5. **Cleanup**: Remove flag and old code paths

### 3. Monitoring

- Set up alerts for flag evaluation errors
- Monitor conversion rates for A/B tests
- Track flag usage to identify unused flags

### 4. Documentation

- Document each flag's purpose and expected behavior
- Include rollback procedures
- Maintain a flag registry with owners and timelines

## Configuration

Feature flags integrate with the configuration service. Key settings:

```python
# Default environment for evaluation
feature_flags.default_environment = "production"

# Enable usage analytics
feature_flags.enable_analytics = true

# Cache TTL for evaluations (seconds)
feature_flags.cache_ttl = 300
```

## Security Considerations

- Feature flags are evaluated server-side to prevent tampering
- Sensitive flags should not be exposed in client-side code
- Use role-based access control for flag management
- Audit all flag changes with user attribution

## Troubleshooting

### Common Issues

1. **Flag not found**: Check flag name spelling and environment
2. **Inconsistent evaluation**: Clear evaluation cache or check user context
3. **Gradual rollout not updating**: Check gradual rollout scheduler
4. **Variant weights error**: Ensure variant weights sum to 100%

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.getLogger("shared.feature_flags").setLevel(logging.DEBUG)
```

## Performance Considerations

- Evaluations are cached for 5 minutes by default
- Use bulk evaluation for multiple flags
- Consider flag complexity impact on evaluation time
- Monitor Redis memory usage for flag storage

## Migration and Cleanup

When removing feature flags:

1. Ensure 100% rollout or 0% rollout
2. Remove flag evaluation code
3. Clean up old code paths
4. Delete the flag from the system
5. Update documentation

The feature flag system provides powerful capabilities for safe, controlled feature releases while maintaining system performance and user experience.