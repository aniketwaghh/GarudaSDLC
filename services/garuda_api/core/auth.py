import time
import os
import requests
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from fastapi import HTTPException, Header

# Cognito Configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
COGNITO_APP_CLIENT_ID = os.getenv("COGNITO_APP_CLIENT_ID")
TOKEN_USE = os.getenv("TOKEN_USE", "id")

if not COGNITO_USER_POOL_ID or not COGNITO_APP_CLIENT_ID:
    raise ValueError("Missing required Cognito configuration in .env")

JWKS_URL = f"https://cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json"
ISSUER = f"https://cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"

# Cache JWKS keys
_jwks_cache: Optional[Dict[str, Any]] = None
_jwks_cache_time: float = 0


def get_jwks() -> Dict[str, Any]:
    """Fetch and cache JWKS from Cognito. Refresh every 10 minutes."""
    global _jwks_cache, _jwks_cache_time
    now = time.time()

    # Return cached JWKS if still valid
    if _jwks_cache and (now - _jwks_cache_time) < 600:  # 10 minutes
        return _jwks_cache

    try:
        response = requests.get(JWKS_URL, timeout=5)
        response.raise_for_status()
        _jwks_cache = response.json()
        _jwks_cache_time = now
        return _jwks_cache
    except requests.RequestException as e:
        raise ValueError(f"Failed to fetch JWKS from Cognito: {str(e)}")


def validate_cognito_token(token: str, token_use: str = TOKEN_USE) -> Dict[str, Any]:
    """
    Validate a Cognito JWT token.
    
    Args:
        token: The JWT token to validate
        token_use: Expected token use ('access' or 'id')
    
    Returns:
        The decoded token payload
    
    Raises:
        ValueError: If token is invalid
    """
    try:
        # Get the key ID from the token header without verification
        headers = jwt.get_unverified_headers(token)
        kid = headers.get("kid")

        if not kid:
            raise ValueError("No 'kid' in token header")

        # Find the matching key in JWKS
        jwks = get_jwks()
        key = None
        for k in jwks.get("keys", []):
            if k["kid"] == kid:
                key = k
                break

        if not key:
            raise ValueError("Public key not found in JWKS")

        # Verify and decode the token
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=COGNITO_APP_CLIENT_ID if token_use == "id" else None,
            issuer=ISSUER,
            options={
                "verify_exp": True,
                "verify_at_hash": False  # Disable at_hash validation for ID tokens
            }
        )

        # Verify token_use claim
        if payload.get("token_use") != token_use:
            raise ValueError(f"Expected {token_use} token, got {payload.get('token_use')}")

        # For access tokens, verify client_id
        if token_use == "access" and payload.get("client_id") != COGNITO_APP_CLIENT_ID:
            raise ValueError("Client ID mismatch")

        return payload

    except JWTError as e:
        raise ValueError(f"JWT validation failed: {str(e)}")
    except Exception as e:
        raise ValueError(f"Token validation error: {str(e)}")


def get_user(authorization: str = Header(None)) -> Dict[str, Any]:
    """
    Extract and validate user from Authorization header.
    
    Args:
        authorization: Authorization header (Bearer token)
    
    Returns:
        User information from the validated token
    
    Raises:
        HTTPException: If token is missing or invalid
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    # Extract token from "Bearer <token>"
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")

    token = authorization[7:]  # Remove "Bearer " prefix

    try:
        # Validate the token
        payload = validate_cognito_token(token)

        return payload

    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Token validation failed")