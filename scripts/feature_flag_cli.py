#!/usr/bin/env python3
"""
Feature Flag CLI Tool

Command-line interface for managing feature flags in the AI Opportunity Browser.
Provides commands for creating, updating, listing, and managing feature flags.

Usage:
    python scripts/feature_flag_cli.py create --name my-feature --description "My feature"
    python scripts/feature_flag_cli.py list
    python scripts/feature_flag_cli.py enable --name my-feature --percentage 50
    python scripts/feature_flag_cli.py disable --name my-feature
    python scripts/feature_flag_cli.py analytics --name my-feature
"""

import asyncio
import argparse
import json
import sys
from datetime import datetime, timedelta
from typing import List, Optional

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
from shared.config_service import ConfigurationService


class FeatureFlagCLI:
    """Command-line interface for feature flag management."""
    
    def __init__(self):
        self.service: Optional[FeatureFlagService] = None
    
    async def initialize(self):
        """Initialize the feature flag service."""
        self.service = FeatureFlagService()
        await self.service.initialize()
    
    async def create_flag(self, args):
        """Create a new feature flag."""
        try:
            # Parse rollout config
            rollout_config = RolloutConfig(
                strategy=RolloutStrategy(args.strategy),
                percentage=args.percentage if args.strategy == "percentage" else None,
                user_ids=args.users.split(',') if args.users else None
            )
            
            # Parse variants
            variants = []
            if args.variants:
                for variant_str in args.variants:
                    name, value, weight = variant_str.split(':')
                    variants.append(FeatureVariant(
                        name=name,
                        value=json.loads(value) if value.startswith(('{', '[', '"')) else value,
                        weight=float(weight)
                    ))
            
            flag = await self.service.create_feature_flag(
                name=args.name,
                description=args.description,
                default_value=json.loads(args.default_value) if args.default_value.startswith(('{', '[', '"')) else args.default_value,
                rollout_config=rollout_config,
                variants=variants if variants else None,
                environments=args.environments.split(',') if args.environments else None,
                tags=args.tags.split(',') if args.tags else None,
                created_by="cli"
            )
            
            print(f"✅ Created feature flag: {flag.name}")
            print(f"   Description: {flag.description}")
            print(f"   Status: {flag.status.value}")
            print(f"   Strategy: {flag.rollout_config.strategy.value}")
            if flag.rollout_config.percentage:
                print(f"   Percentage: {flag.rollout_config.percentage}%")
            
        except Exception as e:
            print(f"❌ Error creating feature flag: {e}")
            return 1
        
        return 0
    
    async def list_flags(self, args):
        """List feature flags."""
        try:
            flags = await self.service.list_feature_flags(
                environment=args.environment,
                status=FeatureFlagStatus(args.status) if args.status else None,
                tags=args.tags.split(',') if args.tags else None
            )
            
            if not flags:
                print("No feature flags found.")
                return 0
            
            print(f"Found {len(flags)} feature flag(s):")
            print()
            
            for flag in flags:
                print(f"🏁 {flag.name}")
                print(f"   Description: {flag.description}")
                print(f"   Status: {flag.status.value}")
                print(f"   Strategy: {flag.rollout_config.strategy.value}")
                if flag.rollout_config.percentage is not None:
                    print(f"   Percentage: {flag.rollout_config.percentage}%")
                print(f"   Environments: {', '.join(flag.environments)}")
                if flag.tags:
                    print(f"   Tags: {', '.join(flag.tags)}")
                print(f"   Updated: {flag.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print()
            
        except Exception as e:
            print(f"❌ Error listing feature flags: {e}")
            return 1
        
        return 0
    
    async def get_flag(self, args):
        """Get details of a specific feature flag."""
        try:
            flag = await self.service.get_feature_flag(args.name)
            if not flag:
                print(f"❌ Feature flag '{args.name}' not found.")
                return 1
            
            print(f"🏁 Feature Flag: {flag.name}")
            print(f"   Description: {flag.description}")
            print(f"   Status: {flag.status.value}")
            print(f"   Default Value: {flag.default_value}")
            print(f"   Strategy: {flag.rollout_config.strategy.value}")
            
            if flag.rollout_config.percentage is not None:
                print(f"   Percentage: {flag.rollout_config.percentage}%")
            
            if flag.rollout_config.user_ids:
                print(f"   Target Users: {len(flag.rollout_config.user_ids)} users")
            
            if flag.variants:
                print(f"   Variants:")
                for variant in flag.variants:
                    print(f"     - {variant.name}: {variant.value} (weight: {variant.weight}%)")
            
            print(f"   Environments: {', '.join(flag.environments)}")
            if flag.tags:
                print(f"   Tags: {', '.join(flag.tags)}")
            
            print(f"   Created: {flag.created_at.strftime('%Y-%m-%d %H:%M:%S')} by {flag.created_by}")
            print(f"   Updated: {flag.updated_at.strftime('%Y-%m-%d %H:%M:%S')} by {flag.updated_by}")
            
        except Exception as e:
            print(f"❌ Error getting feature flag: {e}")
            return 1
        
        return 0
    
    async def enable_flag(self, args):
        """Enable a feature flag with optional percentage."""
        try:
            flag = await self.service.get_feature_flag(args.name)
            if not flag:
                print(f"❌ Feature flag '{args.name}' not found.")
                return 1
            
            # Update rollout config
            rollout_config = flag.rollout_config
            rollout_config.strategy = RolloutStrategy.PERCENTAGE
            rollout_config.percentage = args.percentage
            
            await self.service.update_feature_flag(
                name=args.name,
                status=FeatureFlagStatus.ACTIVE,
                rollout_config=rollout_config,
                updated_by="cli"
            )
            
            print(f"✅ Enabled feature flag '{args.name}' with {args.percentage}% rollout")
            
        except Exception as e:
            print(f"❌ Error enabling feature flag: {e}")
            return 1
        
        return 0
    
    async def disable_flag(self, args):
        """Disable a feature flag."""
        try:
            await self.service.update_feature_flag(
                name=args.name,
                status=FeatureFlagStatus.INACTIVE,
                updated_by="cli"
            )
            
            print(f"✅ Disabled feature flag '{args.name}'")
            
        except Exception as e:
            print(f"❌ Error disabling feature flag: {e}")
            return 1
        
        return 0
    
    async def delete_flag(self, args):
        """Delete a feature flag."""
        try:
            if not args.force:
                response = input(f"Are you sure you want to delete '{args.name}'? (y/N): ")
                if response.lower() != 'y':
                    print("Cancelled.")
                    return 0
            
            deleted = await self.service.delete_feature_flag(args.name, deleted_by="cli")
            if deleted:
                print(f"✅ Deleted feature flag '{args.name}'")
            else:
                print(f"❌ Feature flag '{args.name}' not found.")
                return 1
            
        except Exception as e:
            print(f"❌ Error deleting feature flag: {e}")
            return 1
        
        return 0
    
    async def evaluate_flag(self, args):
        """Evaluate a feature flag for a user."""
        try:
            user_context = UserContext(
                user_id=args.user_id,
                email=args.email,
                role=args.role,
                plan=args.plan,
                country=args.country,
                attributes=json.loads(args.attributes) if args.attributes else None
            )
            
            evaluation = await self.service.evaluate_feature_flag(
                flag_name=args.name,
                user_context=user_context,
                environment=args.environment
            )
            
            print(f"🔍 Evaluation for '{args.name}':")
            print(f"   User: {args.user_id}")
            print(f"   Enabled: {evaluation.enabled}")
            print(f"   Value: {evaluation.value}")
            if evaluation.variant:
                print(f"   Variant: {evaluation.variant}")
            print(f"   Reason: {evaluation.reason}")
            print(f"   Evaluated at: {evaluation.evaluated_at.strftime('%Y-%m-%d %H:%M:%S')}")
            
        except Exception as e:
            print(f"❌ Error evaluating feature flag: {e}")
            return 1
        
        return 0
    
    async def show_analytics(self, args):
        """Show analytics for a feature flag."""
        try:
            start_date = datetime.now() - timedelta(days=args.days)
            end_date = datetime.now()
            
            analytics = await self.service.get_feature_analytics(
                flag_name=args.name,
                start_date=start_date,
                end_date=end_date,
                environment=args.environment
            )
            
            if not analytics:
                print(f"No analytics data found for '{args.name}'")
                return 0
            
            print(f"📊 Analytics for '{args.name}' (last {args.days} days):")
            print(f"   Environment: {analytics['environment']}")
            print(f"   Total Evaluations: {analytics['total_evaluations']}")
            print(f"   Enabled: {analytics['enabled_count']} ({analytics['enabled_count']/max(analytics['total_evaluations'], 1)*100:.1f}%)")
            print(f"   Disabled: {analytics['disabled_count']} ({analytics['disabled_count']/max(analytics['total_evaluations'], 1)*100:.1f}%)")
            print(f"   Unique Users: {analytics['unique_users']}")
            
            if analytics['variants']:
                print(f"   Variants:")
                for variant, count in analytics['variants'].items():
                    print(f"     - {variant}: {count} evaluations")
            
            if args.daily and analytics['daily_stats']:
                print(f"   Daily Stats:")
                for date, stats in sorted(analytics['daily_stats'].items()):
                    print(f"     {date}: {stats['enabled']} enabled, {stats['disabled']} disabled, {stats['unique_users']} users")
            
        except Exception as e:
            print(f"❌ Error getting analytics: {e}")
            return 1
        
        return 0
    
    async def export_flags(self, args):
        """Export feature flags to JSON."""
        try:
            flags = await self.service.list_feature_flags(
                environment=args.environment,
                status=FeatureFlagStatus(args.status) if args.status else None
            )
            
            export_data = []
            for flag in flags:
                flag_data = flag.dict()
                # Convert datetime objects to ISO strings
                flag_data['created_at'] = flag.created_at.isoformat()
                flag_data['updated_at'] = flag.updated_at.isoformat()
                if flag.rollout_config.start_date:
                    flag_data['rollout_config']['start_date'] = flag.rollout_config.start_date.isoformat()
                if flag.rollout_config.end_date:
                    flag_data['rollout_config']['end_date'] = flag.rollout_config.end_date.isoformat()
                export_data.append(flag_data)
            
            with open(args.output, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            print(f"✅ Exported {len(flags)} feature flags to {args.output}")
            
        except Exception as e:
            print(f"❌ Error exporting feature flags: {e}")
            return 1
        
        return 0


def create_parser():
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description="Feature Flag CLI for AI Opportunity Browser",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new feature flag')
    create_parser.add_argument('--name', required=True, help='Feature flag name')
    create_parser.add_argument('--description', required=True, help='Feature flag description')
    create_parser.add_argument('--default-value', default='false', help='Default value (default: false)')
    create_parser.add_argument('--strategy', choices=['percentage', 'user_list', 'user_attribute'], 
                              default='percentage', help='Rollout strategy (default: percentage)')
    create_parser.add_argument('--percentage', type=float, default=0.0, help='Rollout percentage (default: 0)')
    create_parser.add_argument('--users', help='Comma-separated list of user IDs')
    create_parser.add_argument('--variants', nargs='*', help='Variants in format name:value:weight')
    create_parser.add_argument('--environments', help='Comma-separated list of environments')
    create_parser.add_argument('--tags', help='Comma-separated list of tags')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List feature flags')
    list_parser.add_argument('--environment', help='Filter by environment')
    list_parser.add_argument('--status', choices=['active', 'inactive', 'archived'], help='Filter by status')
    list_parser.add_argument('--tags', help='Filter by tags (comma-separated)')
    
    # Get command
    get_parser = subparsers.add_parser('get', help='Get feature flag details')
    get_parser.add_argument('--name', required=True, help='Feature flag name')
    
    # Enable command
    enable_parser = subparsers.add_parser('enable', help='Enable a feature flag')
    enable_parser.add_argument('--name', required=True, help='Feature flag name')
    enable_parser.add_argument('--percentage', type=float, default=100.0, help='Rollout percentage (default: 100)')
    
    # Disable command
    disable_parser = subparsers.add_parser('disable', help='Disable a feature flag')
    disable_parser.add_argument('--name', required=True, help='Feature flag name')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a feature flag')
    delete_parser.add_argument('--name', required=True, help='Feature flag name')
    delete_parser.add_argument('--force', action='store_true', help='Skip confirmation')
    
    # Evaluate command
    evaluate_parser = subparsers.add_parser('evaluate', help='Evaluate a feature flag for a user')
    evaluate_parser.add_argument('--name', required=True, help='Feature flag name')
    evaluate_parser.add_argument('--user-id', required=True, help='User ID')
    evaluate_parser.add_argument('--email', help='User email')
    evaluate_parser.add_argument('--role', help='User role')
    evaluate_parser.add_argument('--plan', help='User plan')
    evaluate_parser.add_argument('--country', help='User country')
    evaluate_parser.add_argument('--attributes', help='User attributes as JSON')
    evaluate_parser.add_argument('--environment', help='Target environment')
    
    # Analytics command
    analytics_parser = subparsers.add_parser('analytics', help='Show feature flag analytics')
    analytics_parser.add_argument('--name', required=True, help='Feature flag name')
    analytics_parser.add_argument('--days', type=int, default=7, help='Number of days to analyze (default: 7)')
    analytics_parser.add_argument('--environment', help='Target environment')
    analytics_parser.add_argument('--daily', action='store_true', help='Show daily breakdown')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export feature flags to JSON')
    export_parser.add_argument('--output', required=True, help='Output file path')
    export_parser.add_argument('--environment', help='Filter by environment')
    export_parser.add_argument('--status', choices=['active', 'inactive', 'archived'], help='Filter by status')
    
    return parser


async def main():
    """Main CLI function."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    cli = FeatureFlagCLI()
    await cli.initialize()
    
    # Route to appropriate command handler
    command_handlers = {
        'create': cli.create_flag,
        'list': cli.list_flags,
        'get': cli.get_flag,
        'enable': cli.enable_flag,
        'disable': cli.disable_flag,
        'delete': cli.delete_flag,
        'evaluate': cli.evaluate_flag,
        'analytics': cli.show_analytics,
        'export': cli.export_flags
    }
    
    handler = command_handlers.get(args.command)
    if handler:
        return await handler(args)
    else:
        print(f"❌ Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)