"""
Two-Factor Authentication Service for the AI Opportunity Browser.

This module provides comprehensive 2FA functionality including TOTP, SMS, 
email-based authentication, and backup code management.
"""

import pyotp
import qrcode
import secrets
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any
from io import BytesIO
from base64 import b64encode
from cryptography.fernet import Fernet

from api.core.config import get_settings
from shared.database import get_redis_client
from shared.models.user import User

logger = logging.getLogger(__name__)
settings = get_settings()


class TwoFactorError(Exception):
    """Base exception for 2FA errors."""
    pass


class InvalidCodeError(TwoFactorError):
    """Exception raised when 2FA code is invalid."""
    pass


class SetupRequiredError(TwoFactorError):
    """Exception raised when 2FA setup is required but not completed."""
    pass


class TwoFactorService:
    """
    Service for managing two-factor authentication functionality.
    """
    
    def __init__(self):
        self.issuer_name = getattr(settings, 'TWO_FACTOR_ISSUER', 'AI Opportunity Browser')
        self.totp_window = getattr(settings, 'TOTP_WINDOW', 1)  # Allow 1 step tolerance
        self.backup_code_count = 10
        self.sms_code_expiry = 300  # 5 minutes
        self.email_code_expiry = 600  # 10 minutes
        
        # Initialize encryption key for secrets
        encryption_key = getattr(settings, 'TWO_FACTOR_ENCRYPTION_KEY', None)
        if not encryption_key:
            # Generate a key - in production, this should be from environment
            encryption_key = Fernet.generate_key()
            logger.warning("Using generated encryption key for 2FA secrets. Set TWO_FACTOR_ENCRYPTION_KEY in production.")
        
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode()
        
        self.cipher = Fernet(encryption_key)
        self.redis_client = get_redis_client()
    
    def generate_totp_secret(self) -> str:
        """
        Generate a new TOTP secret key.
        
        Returns:
            Base32 encoded secret key
        """
        return pyotp.random_base32()
    
    def encrypt_secret(self, secret: str) -> str:
        """
        Encrypt a secret for database storage.
        
        Args:
            secret: Plain text secret
            
        Returns:
            Encrypted secret as string
        """
        return self.cipher.encrypt(secret.encode()).decode()
    
    def decrypt_secret(self, encrypted_secret: str) -> str:
        """
        Decrypt a secret from database storage.
        
        Args:
            encrypted_secret: Encrypted secret string
            
        Returns:
            Plain text secret
        """
        return self.cipher.decrypt(encrypted_secret.encode()).decode()
    
    def generate_qr_code(self, user_email: str, secret: str) -> str:
        """
        Generate QR code for TOTP setup.
        
        Args:
            user_email: User's email address
            secret: TOTP secret key
            
        Returns:
            Base64 encoded QR code image
        """
        # Create TOTP URI
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user_email,
            issuer_name=self.issuer_name
        )
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return b64encode(buffer.getvalue()).decode()
    
    def generate_backup_codes(self) -> List[str]:
        """
        Generate backup codes for 2FA recovery.
        
        Returns:
            List of backup codes
        """
        codes = []
        for _ in range(self.backup_code_count):
            # Generate 8-digit backup code
            code = ''.join([str(secrets.randbelow(10)) for _ in range(8)])
            codes.append(code)
        
        return codes
    
    def verify_totp_code(self, secret: str, code: str) -> bool:
        """
        Verify a TOTP code.
        
        Args:
            secret: TOTP secret key
            code: 6-digit TOTP code
            
        Returns:
            True if code is valid
        """
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(code, valid_window=self.totp_window)
        except Exception as e:
            logger.error(f"TOTP verification error: {e}")
            return False
    
    def setup_totp(self, user: User) -> Dict[str, Any]:
        """
        Setup TOTP for a user.
        
        Args:
            user: User object
            
        Returns:
            Dictionary containing setup information
        """
        try:
            # Generate secret
            secret = self.generate_totp_secret()
            
            # Generate QR code
            qr_code = self.generate_qr_code(user.email, secret)
            
            # Generate backup codes
            backup_codes = self.generate_backup_codes()
            
            # Store temporary setup data in Redis (expires in 10 minutes)
            setup_key = f"2fa_setup:{user.id}"
            setup_data = {
                "secret": secret,
                "backup_codes": backup_codes,
                "method": "totp",
                "created_at": datetime.utcnow().isoformat()
            }
            
            self.redis_client.setex(
                setup_key,
                600,  # 10 minutes
                json.dumps(setup_data)
            )
            
            logger.info(f"TOTP setup initiated for user {user.email}")
            
            return {
                "secret": secret,
                "qr_code": qr_code,
                "backup_codes": backup_codes,
                "method": "totp"
            }
            
        except Exception as e:
            logger.error(f"TOTP setup error for user {user.email}: {e}")
            raise TwoFactorError(f"Failed to setup TOTP: {e}")
    
    def verify_setup_code(self, user: User, code: str) -> bool:
        """
        Verify code during 2FA setup process.
        
        Args:
            user: User object
            code: Verification code
            
        Returns:
            True if setup should be completed
        """
        try:
            setup_key = f"2fa_setup:{user.id}"
            setup_data_json = self.redis_client.get(setup_key)
            
            if not setup_data_json:
                raise SetupRequiredError("No active 2FA setup found")
            
            setup_data = json.loads(setup_data_json)
            secret = setup_data["secret"]
            method = setup_data["method"]
            
            if method == "totp":
                if self.verify_totp_code(secret, code):
                    logger.info(f"2FA setup verification successful for user {user.email}")
                    return True
            elif method == "sms":
                # Verify SMS code (implementation depends on SMS provider)
                if self.verify_sms_code(user.phone_number, code):
                    return True
            elif method == "email":
                # Verify email code
                if self.verify_email_code(user.email, code):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Setup verification error for user {user.email}: {e}")
            raise TwoFactorError(f"Setup verification failed: {e}")
    
    def complete_setup(self, user: User) -> Dict[str, Any]:
        """
        Complete 2FA setup and enable it for the user.
        
        Args:
            user: User object
            
        Returns:
            Dictionary with completion status
        """
        try:
            setup_key = f"2fa_setup:{user.id}"
            setup_data_json = self.redis_client.get(setup_key)
            
            if not setup_data_json:
                raise SetupRequiredError("No active 2FA setup found")
            
            setup_data = json.loads(setup_data_json)
            
            # Encrypt and store the secret
            encrypted_secret = self.encrypt_secret(setup_data["secret"])
            encrypted_backup_codes = self.encrypt_secret(json.dumps(setup_data["backup_codes"]))
            
            # Update user record (this would need to be done in the calling function)
            # user.two_factor_enabled = True
            # user.totp_secret = encrypted_secret
            # user.backup_codes = encrypted_backup_codes
            # user.two_factor_method = setup_data["method"]
            
            # Clean up setup data
            self.redis_client.delete(setup_key)
            
            logger.info(f"2FA setup completed for user {user.email}")
            
            return {
                "enabled": True,
                "method": setup_data["method"],
                "backup_codes_remaining": len(setup_data["backup_codes"])
            }
            
        except Exception as e:
            logger.error(f"Setup completion error for user {user.email}: {e}")
            raise TwoFactorError(f"Failed to complete setup: {e}")
    
    def verify_code(self, user: User, code: str, method: Optional[str] = None) -> bool:
        """
        Verify a 2FA code for authentication.
        
        Args:
            user: User object
            code: 2FA code to verify
            method: Optional method override
            
        Returns:
            True if code is valid
        """
        try:
            if not user.two_factor_enabled:
                raise TwoFactorError("2FA not enabled for user")
            
            # Determine verification method
            verify_method = method or user.two_factor_method or "totp"
            
            if verify_method == "totp":
                if not user.totp_secret:
                    raise TwoFactorError("TOTP not configured")
                
                secret = self.decrypt_secret(user.totp_secret)
                return self.verify_totp_code(secret, code)
            
            elif verify_method == "backup":
                return self.verify_backup_code(user, code)
            
            elif verify_method == "sms":
                return self.verify_sms_code(user.phone_number, code)
            
            elif verify_method == "email":
                return self.verify_email_code(user.email, code)
            
            else:
                raise TwoFactorError(f"Unsupported 2FA method: {verify_method}")
                
        except Exception as e:
            logger.error(f"2FA verification error for user {user.email}: {e}")
            return False
    
    def verify_backup_code(self, user: User, code: str) -> bool:
        """
        Verify a backup code.
        
        Args:
            user: User object
            code: Backup code to verify
            
        Returns:
            True if backup code is valid and unused
        """
        try:
            if not user.backup_codes:
                return False
            
            # Decrypt backup codes
            backup_codes = json.loads(self.decrypt_secret(user.backup_codes))
            
            # Get used backup codes
            used_codes = []
            if user.backup_codes_used:
                used_codes = json.loads(user.backup_codes_used)
            
            # Check if code is valid and unused
            if code in backup_codes and code not in used_codes:
                # Mark code as used (this would need to be done in the calling function)
                # used_codes.append(code)
                # user.backup_codes_used = json.dumps(used_codes)
                
                logger.info(f"Backup code used for user {user.email}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Backup code verification error: {e}")
            return False
    
    def send_sms_code(self, phone_number: str) -> str:
        """
        Send SMS 2FA code.
        
        Args:
            phone_number: Phone number to send code to
            
        Returns:
            Code sent (for testing, remove in production)
        """
        try:
            # Generate 6-digit SMS code
            code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
            
            # Store code in Redis with expiration
            sms_key = f"sms_code:{phone_number}"
            self.redis_client.setex(sms_key, self.sms_code_expiry, code)
            
            # TODO: Send SMS using Twilio, AWS SNS, or other provider
            # For now, just log the code (remove in production)
            logger.info(f"SMS code for {phone_number}: {code}")
            
            return code  # Remove this in production
            
        except Exception as e:
            logger.error(f"SMS sending error: {e}")
            raise TwoFactorError(f"Failed to send SMS: {e}")
    
    def verify_sms_code(self, phone_number: str, code: str) -> bool:
        """
        Verify SMS 2FA code.
        
        Args:
            phone_number: Phone number the code was sent to
            code: SMS code to verify
            
        Returns:
            True if code is valid
        """
        try:
            sms_key = f"sms_code:{phone_number}"
            stored_code = self.redis_client.get(sms_key)
            
            if stored_code and stored_code.decode() == code:
                # Remove code after successful verification
                self.redis_client.delete(sms_key)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"SMS verification error: {e}")
            return False
    
    def send_email_code(self, email: str) -> str:
        """
        Send email 2FA code.
        
        Args:
            email: Email address to send code to
            
        Returns:
            Code sent (for testing, remove in production)
        """
        try:
            # Generate 6-digit email code
            code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
            
            # Store code in Redis with expiration
            email_key = f"email_code:{email}"
            self.redis_client.setex(email_key, self.email_code_expiry, code)
            
            # TODO: Send email using configured email service
            # For now, just log the code (remove in production)
            logger.info(f"Email code for {email}: {code}")
            
            return code  # Remove this in production
            
        except Exception as e:
            logger.error(f"Email sending error: {e}")
            raise TwoFactorError(f"Failed to send email: {e}")
    
    def verify_email_code(self, email: str, code: str) -> bool:
        """
        Verify email 2FA code.
        
        Args:
            email: Email address the code was sent to
            code: Email code to verify
            
        Returns:
            True if code is valid
        """
        try:
            email_key = f"email_code:{email}"
            stored_code = self.redis_client.get(email_key)
            
            if stored_code and stored_code.decode() == code:
                # Remove code after successful verification
                self.redis_client.delete(email_key)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Email verification error: {e}")
            return False
    
    def disable_two_factor(self, user: User) -> Dict[str, Any]:
        """
        Disable 2FA for a user.
        
        Args:
            user: User object
            
        Returns:
            Status dictionary
        """
        try:
            # Clear 2FA data (this would need to be done in the calling function)
            # user.two_factor_enabled = False
            # user.totp_secret = None
            # user.backup_codes = None
            # user.backup_codes_used = None
            # user.two_factor_method = None
            
            # Clean up any pending setup
            setup_key = f"2fa_setup:{user.id}"
            self.redis_client.delete(setup_key)
            
            logger.info(f"2FA disabled for user {user.email}")
            
            return {
                "disabled": True,
                "message": "Two-factor authentication has been disabled"
            }
            
        except Exception as e:
            logger.error(f"2FA disable error for user {user.email}: {e}")
            raise TwoFactorError(f"Failed to disable 2FA: {e}")
    
    def regenerate_backup_codes(self, user: User) -> List[str]:
        """
        Regenerate backup codes for a user.
        
        Args:
            user: User object
            
        Returns:
            New backup codes
        """
        try:
            if not user.two_factor_enabled:
                raise TwoFactorError("2FA not enabled")
            
            # Generate new backup codes
            new_codes = self.generate_backup_codes()
            encrypted_codes = self.encrypt_secret(json.dumps(new_codes))
            
            # Update user record (this would need to be done in the calling function)
            # user.backup_codes = encrypted_codes
            # user.backup_codes_used = None  # Reset used codes
            
            logger.info(f"Backup codes regenerated for user {user.email}")
            
            return new_codes
            
        except Exception as e:
            logger.error(f"Backup code regeneration error: {e}")
            raise TwoFactorError(f"Failed to regenerate backup codes: {e}")
    
    def get_two_factor_status(self, user: User) -> Dict[str, Any]:
        """
        Get 2FA status for a user.
        
        Args:
            user: User object
            
        Returns:
            Status dictionary
        """
        try:
            if not user.two_factor_enabled:
                return {
                    "enabled": False,
                    "method": None,
                    "backup_codes_remaining": 0
                }
            
            # Count remaining backup codes
            backup_codes_remaining = 0
            if user.backup_codes:
                backup_codes = json.loads(self.decrypt_secret(user.backup_codes))
                used_codes = []
                if user.backup_codes_used:
                    used_codes = json.loads(user.backup_codes_used)
                backup_codes_remaining = len(backup_codes) - len(used_codes)
            
            return {
                "enabled": True,
                "method": user.two_factor_method,
                "backup_codes_remaining": backup_codes_remaining
            }
            
        except Exception as e:
            logger.error(f"Status check error for user {user.email}: {e}")
            return {
                "enabled": False,
                "method": None,
                "backup_codes_remaining": 0,
                "error": str(e)
            }


# Global service instance
two_factor_service = TwoFactorService()