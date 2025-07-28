#!/usr/bin/env python3
"""
Test script for zero trust security architecture implementation.

This script validates the zero trust security features including:
- Service-to-service authentication
- User authentication with trust levels
- Security monitoring and alerting
- Threat detection
"""

import asyncio
import sys
import os
from datetime import datetime, timezone
from typing import Dict, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.security.zero_trust import (
    setup_zero_trust,
    SecurityPrincipal,
    SecurityRequest,
    SecurityContext,
    TrustLevel,
    ZeroTrustManager
)
from shared.security.service_config import setup_service_registry
from shared.security.monitoring import (
    setup_security_monitoring,
    SecurityEvent,
    SecurityEventType,
    SecuritySeverity,
    log_authentication_success,
    log_authentication_failure,
    log_authorization_denied,
    log_suspicious_activity
)


class ZeroTrustSecurityTester:
    """Test suite for zero trust security architecture."""
    
    def __init__(self):
        """Initialize the tester."""
        self.service_registry = None
        self.zt_manager = None
        self.security_monitor = None
        self.test_results = []
    
    async def setup(self):
        """Setup test environment."""
        print("🔧 Setting up zero trust security test environment...")
        
        # Setup service registry
        self.service_registry = setup_service_registry()
        
        # Setup zero trust manager
        service_secrets = self.service_registry.get_service_secrets()
        self.zt_manager = setup_zero_trust(service_secrets)
        
        # Setup security monitoring
        self.security_monitor = setup_security_monitoring()
        
        print("✅ Test environment setup complete")
    
    def log_test_result(self, test_name: str, success: bool, message: str = ""):
        """Log a test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if message:
            print(f"    {message}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message
        })
    
    async def test_service_authentication(self):
        """Test service-to-service authentication."""
        print("\n🔐 Testing service-to-service authentication...")
        
        try:
            # Test generating service token
            token = self.zt_manager.service_auth.generate_service_token(
                "ai-opportunity-browser-api",
                "data-ingestion-service",
                expires_in=3600
            )
            
            self.log_test_result(
                "Service token generation",
                bool(token),
                f"Generated token: {token[:20]}..."
            )
            
            # Test verifying service token
            principal = self.zt_manager.service_auth.verify_service_token(
                token,
                "data-ingestion-service"
            )
            
            self.log_test_result(
                "Service token verification",
                principal.type == "service" and principal.name == "ai-opportunity-browser-api",
                f"Principal: {principal.name} ({principal.type})"
            )
            
            # Test invalid service token
            try:
                self.zt_manager.service_auth.verify_service_token(
                    "invalid_token",
                    "data-ingestion-service"
                )
                self.log_test_result("Invalid token rejection", False, "Should have failed")
            except Exception:
                self.log_test_result("Invalid token rejection", True, "Correctly rejected invalid token")
            
        except Exception as e:
            self.log_test_result("Service authentication", False, f"Error: {e}")
    
    async def test_user_authentication(self):
        """Test user authentication with trust levels."""
        print("\n👤 Testing user authentication...")
        
        try:
            # Create mock user principals with different trust levels
            user_principal = SecurityPrincipal(
                id="user123",
                type="user",
                name="testuser",
                roles=["user"],
                permissions=["read:opportunities"],
                trust_level=TrustLevel.LOW
            )
            
            expert_principal = SecurityPrincipal(
                id="expert456",
                type="user",
                name="expertuser",
                roles=["expert"],
                permissions=["read:opportunities", "create:validations"],
                trust_level=TrustLevel.MEDIUM
            )
            
            admin_principal = SecurityPrincipal(
                id="admin789",
                type="user",
                name="adminuser",
                roles=["admin"],
                permissions=["*"],
                trust_level=TrustLevel.VERIFIED
            )
            
            # Test trust level checks
            self.log_test_result(
                "User trust level check",
                user_principal.is_trusted(TrustLevel.LOW),
                f"User trust level: {user_principal.trust_level.value}"
            )
            
            self.log_test_result(
                "Expert trust level check",
                expert_principal.is_trusted(TrustLevel.MEDIUM),
                f"Expert trust level: {expert_principal.trust_level.value}"
            )
            
            self.log_test_result(
                "Admin trust level check",
                admin_principal.is_trusted(TrustLevel.VERIFIED),
                f"Admin trust level: {admin_principal.trust_level.value}"
            )
            
        except Exception as e:
            self.log_test_result("User authentication", False, f"Error: {e}")
    
    async def test_zero_trust_evaluation(self):
        """Test zero trust request evaluation."""
        print("\n🛡️ Testing zero trust request evaluation...")
        
        try:
            # Create test principals
            user_principal = SecurityPrincipal(
                id="user123",
                type="user",
                name="testuser",
                roles=["user"],
                permissions=["read:opportunities"],
                trust_level=TrustLevel.LOW
            )
            
            admin_principal = SecurityPrincipal(
                id="admin789",
                type="user",
                name="adminuser",
                roles=["admin"],
                permissions=["*"],
                trust_level=TrustLevel.VERIFIED
            )
            
            # Test public access
            public_request = SecurityRequest(
                principal=user_principal,
                resource="/health",
                action="read",
                context=SecurityContext.PUBLIC,
                ip_address="192.168.1.100"
            )
            
            decision = self.zt_manager.authorize_request(public_request)
            self.log_test_result(
                "Public access authorization",
                decision.allowed,
                f"Decision: {decision.reason}"
            )
            
            # Test authenticated access
            auth_request = SecurityRequest(
                principal=user_principal,
                resource="/api/v1/opportunities",
                action="read",
                context=SecurityContext.AUTHENTICATED,
                ip_address="192.168.1.100"
            )
            
            decision = self.zt_manager.authorize_request(auth_request)
            self.log_test_result(
                "Authenticated access authorization",
                decision.allowed,
                f"Decision: {decision.reason}"
            )
            
            # Test admin access
            admin_request = SecurityRequest(
                principal=admin_principal,
                resource="/admin/users",
                action="write",
                context=SecurityContext.ADMIN,
                ip_address="192.168.1.100"
            )
            
            decision = self.zt_manager.authorize_request(admin_request)
            self.log_test_result(
                "Admin access authorization",
                decision.allowed,
                f"Decision: {decision.reason}"
            )
            
            # Test unauthorized access
            unauth_request = SecurityRequest(
                principal=user_principal,
                resource="/admin/users",
                action="write",
                context=SecurityContext.ADMIN,
                ip_address="192.168.1.100"
            )
            
            decision = self.zt_manager.authorize_request(unauth_request)
            self.log_test_result(
                "Unauthorized access denial",
                not decision.allowed,
                f"Decision: {decision.reason}"
            )
            
        except Exception as e:
            self.log_test_result("Zero trust evaluation", False, f"Error: {e}")
    
    async def test_security_monitoring(self):
        """Test security monitoring and alerting."""
        print("\n📊 Testing security monitoring...")
        
        try:
            # Log various security events
            log_authentication_success("user123", "192.168.1.100", user_agent="TestAgent/1.0")
            log_authentication_failure("192.168.1.101", "Invalid credentials", user_agent="AttackBot/1.0")
            log_authorization_denied("user123", "/admin/users", "write", reason="Insufficient privileges")
            log_suspicious_activity("user456", "Multiple rapid requests", SecuritySeverity.MEDIUM)
            
            # Simulate brute force attack
            for i in range(6):  # Exceed brute force threshold
                log_authentication_failure("192.168.1.102", f"Brute force attempt {i+1}")
            
            # Get security summary
            summary = self.security_monitor.get_security_summary()
            
            self.log_test_result(
                "Security event logging",
                summary["events_24h"] > 0,
                f"Logged {summary['events_24h']} events in last 24h"
            )
            
            # Check for alerts
            active_alerts = self.security_monitor.get_active_alerts()
            
            self.log_test_result(
                "Security alert generation",
                len(active_alerts) > 0,
                f"Generated {len(active_alerts)} active alerts"
            )
            
            # Test alert acknowledgment
            if active_alerts:
                alert_id = active_alerts[0].alert_id
                self.security_monitor.acknowledge_alert(alert_id)
                
                self.log_test_result(
                    "Alert acknowledgment",
                    self.security_monitor.alerts[alert_id].acknowledged,
                    f"Acknowledged alert: {alert_id}"
                )
            
        except Exception as e:
            self.log_test_result("Security monitoring", False, f"Error: {e}")
    
    async def test_service_registry(self):
        """Test service registry functionality."""
        print("\n📋 Testing service registry...")
        
        try:
            # Get all services
            services = self.service_registry.get_all_services()
            
            self.log_test_result(
                "Service registry population",
                len(services) > 0,
                f"Registered {len(services)} services"
            )
            
            # Test service lookup
            api_service = self.service_registry.get_service("ai-opportunity-browser-api")
            
            self.log_test_result(
                "Service lookup",
                api_service is not None,
                f"Found service: {api_service.name if api_service else 'None'}"
            )
            
            # Test service secret retrieval
            secret = self.service_registry.get_service_secret("ai-opportunity-browser-api")
            
            self.log_test_result(
                "Service secret retrieval",
                secret is not None,
                f"Retrieved secret: {secret[:10]}..." if secret else "No secret"
            )
            
            # Test service secret rotation
            old_secret = secret
            new_secret = self.service_registry.rotate_service_secret("ai-opportunity-browser-api")
            
            self.log_test_result(
                "Service secret rotation",
                new_secret != old_secret,
                "Secret successfully rotated"
            )
            
        except Exception as e:
            self.log_test_result("Service registry", False, f"Error: {e}")
    
    async def run_all_tests(self):
        """Run all security tests."""
        print("🚀 Starting Zero Trust Security Architecture Tests")
        print("=" * 60)
        
        await self.setup()
        
        # Run individual test suites
        await self.test_service_authentication()
        await self.test_user_authentication()
        await self.test_zero_trust_evaluation()
        await self.test_security_monitoring()
        await self.test_service_registry()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['message']}")
        
        print("\n🎉 Zero Trust Security Architecture testing complete!")
        return failed_tests == 0


async def main():
    """Main test function."""
    tester = ZeroTrustSecurityTester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n✅ All tests passed! Zero trust security architecture is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())