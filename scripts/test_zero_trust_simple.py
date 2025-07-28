#!/usr/bin/env python3
"""
Simple test for zero trust security components.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test importing zero trust components."""
    try:
        print("Testing basic imports...")
        
        # Test enum imports
        from shared.security.zero_trust import TrustLevel, SecurityContext
        print("✅ Enums imported successfully")
        
        # Test dataclass imports
        from shared.security.zero_trust import SecurityPrincipal
        print("✅ SecurityPrincipal imported successfully")
        
        # Test other classes
        from shared.security.zero_trust import ServiceAuthenticator, ZeroTrustEvaluator
        print("✅ Core classes imported successfully")
        
        # Test manager
        from shared.security.zero_trust import ZeroTrustManager
        print("✅ ZeroTrustManager imported successfully")
        
        # Test setup functions
        from shared.security.zero_trust import setup_zero_trust, get_zero_trust_manager
        print("✅ Setup functions imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality."""
    try:
        from shared.security.zero_trust import TrustLevel, SecurityPrincipal
        
        # Create a security principal
        principal = SecurityPrincipal(
            id="test123",
            type="user",
            name="testuser",
            roles=["user"],
            permissions=["read"],
            trust_level=TrustLevel.LOW
        )
        
        print(f"✅ Created security principal: {principal.name}")
        print(f"   Trust level: {principal.trust_level.value}")
        print(f"   Has role 'user': {principal.has_role('user')}")
        print(f"   Has permission 'read': {principal.has_permission('read')}")
        print(f"   Is trusted (LOW): {principal.is_trusted(TrustLevel.LOW)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Functionality test error: {e}")
        return False

def main():
    """Main test function."""
    print("🔧 Testing Zero Trust Security Components")
    print("=" * 50)
    
    # Test imports
    if not test_imports():
        print("❌ Import tests failed")
        return False
    
    print()
    
    # Test basic functionality
    if not test_basic_functionality():
        print("❌ Functionality tests failed")
        return False
    
    print("\n✅ All basic tests passed!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)