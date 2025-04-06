from fastapi import HTTPException, Header, status
from typing import Optional
from .utils import IS_BFF_SERVICE, VALID_SUBJECTS, VALID_ISSUER
import jwt
import time

async def validate_client_type(x_client_type: Optional[str] = Header(None)):
    if IS_BFF_SERVICE:
        if not x_client_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing X-Client-Type header"
            )
        valid_types = {"web", "ios", "android"}
        if x_client_type.lower() not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid X-Client-Type header: {x_client_type}. Must be one of: Web, iOS, Android"
            )
    return x_client_type

async def validate_auth(authorization: Optional[str] = Header(None)):
    if IS_BFF_SERVICE:
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Authorization header"
            )
        validate_jwt_token(authorization)
    return authorization

def validate_jwt_token(token: str):
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]

        # Decode and validate the token
        payload = jwt.decode(token, options={"verify_signature": False})
        
        # Check required claims
        if 'sub' not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing 'sub' claim in token"
            )
        if 'exp' not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing 'exp' claim in token"
            )
        if 'iss' not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing 'iss' claim in token"
            )

        # Validate claim values
        if payload['sub'] not in VALID_SUBJECTS:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 'sub' claim in token"
            )
        if payload['iss'] != VALID_ISSUER:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 'iss' claim in token"
            )

        # Check if token is expired
        exp_timestamp = payload['exp']
        current_timestamp = int(time.time())
        if current_timestamp > exp_timestamp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        ) 