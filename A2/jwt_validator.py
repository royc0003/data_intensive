from fastapi import HTTPException, status
import jwt
from datetime import datetime

# Constants for validation
VALID_SUBJECTS = {"starlord", "gamora", "drax", "rocket", "groot"}
VALID_ISSUER = "cmu.edu"

def validate_jwt_token(authorization: str) -> dict:
    """
    Validates a JWT token from the Authorization header.
    Returns the decoded payload if valid.
    Raises HTTPException with 401 status if invalid.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header"
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    token = authorization.split(" ")[1]
    try:
        # Decode the JWT token (without verification for this assignment)
        payload = jwt.decode(token, options={"verify_signature": False})
        
        # Validate required claims
        if "sub" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing subject claim"
            )
        
        if payload["sub"] not in VALID_SUBJECTS:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid subject in token"
            )
        
        if "exp" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing expiration claim"
            )
        
        # Check if token is expired
        exp_timestamp = payload["exp"]
        if datetime.fromtimestamp(exp_timestamp) < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        
        if "iss" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing issuer claim"
            )
        
        if payload["iss"] != VALID_ISSUER:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid issuer"
            )
        
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        ) 