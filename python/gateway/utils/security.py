"""
Security utilities for the AI Gateway.
"""
import secrets
import hashlib
import hmac
import base64
import logging
from typing import Optional


logger = logging.getLogger(__name__)


def generate_api_key(length: int = 32) -> str:
    """
    Generate a secure API key.
    
    Args:
        length: Length of the key in bytes (default: 32)
        
    Returns:
        Base64-encoded API key
    """
    # Generate random bytes
    random_bytes = secrets.token_bytes(length)
    
    # Encode as base64
    api_key = base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')
    
    # Add prefix for better usability
    return f"gw-{api_key}"


def hash_api_key(api_key: str, salt: Optional[str] = None) -> str:
    """
    Hash an API key for storage.
    
    Args:
        api_key: API key to hash
        salt: Optional salt (if not provided, a random salt will be generated)
        
    Returns:
        Hashed API key with salt
    """
    # Generate salt if not provided
    if salt is None:
        salt = secrets.token_hex(16)
    
    # Hash the API key with the salt
    key_bytes = api_key.encode('utf-8')
    salt_bytes = salt.encode('utf-8')
    
    # Use PBKDF2 for secure key hashing
    hashed_key = hashlib.pbkdf2_hmac(
        'sha256',
        key_bytes,
        salt_bytes,
        100000,  # Number of iterations
        dklen=32  # Length of the derived key
    )
    
    # Encode as hex
    hashed_key_hex = hashed_key.hex()
    
    # Return hashed key with salt
    return f"{salt}${hashed_key_hex}"


def verify_api_key(api_key: str, hashed_key: str) -> bool:
    """
    Verify an API key against its hashed value.
    
    Args:
        api_key: API key to verify
        hashed_key: Hashed API key to compare against
        
    Returns:
        True if the API key matches the hashed key, False otherwise
    """
    # Extract salt from hashed key
    salt, stored_hash = hashed_key.split('$', 1)
    
    # Hash the API key with the salt
    key_bytes = api_key.encode('utf-8')
    salt_bytes = salt.encode('utf-8')
    
    # Use PBKDF2 for secure key hashing
    hashed_key = hashlib.pbkdf2_hmac(
        'sha256',
        key_bytes,
        salt_bytes,
        100000,  # Number of iterations
        dklen=32  # Length of the derived key
    )
    
    # Encode as hex
    hashed_key_hex = hashed_key.hex()
    
    # Compare hashed keys (constant-time comparison)
    return hmac.compare_digest(stored_hash, hashed_key_hex)


def generate_webhook_signature(payload: str, secret: str) -> str:
    """
    Generate a signature for a webhook payload.
    
    Args:
        payload: Webhook payload
        secret: Webhook secret
        
    Returns:
        Signature for the payload
    """
    # Create HMAC with SHA-256
    signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return signature


def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    """
    Verify a webhook signature.
    
    Args:
        payload: Webhook payload
        signature: Signature to verify
        secret: Webhook secret
        
    Returns:
        True if the signature is valid, False otherwise
    """
    # Generate signature
    expected_signature = generate_webhook_signature(payload, secret)
    
    # Compare signatures (constant-time comparison)
    return hmac.compare_digest(signature, expected_signature)