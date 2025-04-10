from fastapi import FastAPI, HTTPException, Header, Response, Query, status, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from typing import Optional, Union, Dict, Any
import httpx
import asyncio
from ..shared.models import Book, CustomerBase, CustomerResponse, MobileCustomerResponse
from ..shared.auth import validate_client_type, validate_auth
import os
import logging
import json
from decimal import Decimal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom JSON encoder to handle Decimal and other non-serializable types
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

app = FastAPI()

# Service URLs
BOOKS_SERVICE_URL = os.getenv("BOOKS_SERVICE_URL", "http://book-service.bookstore-ns:3000")
CUSTOMERS_SERVICE_URL = os.getenv("CUSTOMERS_SERVICE_URL", "http://book-service.bookstore-ns:3000")

# Timeout settings
REQUEST_TIMEOUT = 30.0  # Overall request timeout in seconds
CONNECT_TIMEOUT = 10.0  # Connection timeout in seconds
MAX_RETRIES = 3
RETRY_DELAY = 1.0

# Special route for health checks that bypasses middleware and validation
@app.get("/status", include_in_schema=False)
def health_check():
    """
    Health check endpoint for AWS ALB
    This route bypasses all validation and middleware
    """
    return PlainTextResponse(content="OK", status_code=200)

# Block any non-status routes that don't have proper headers
@app.middleware("http")
async def validate_headers_middleware(request: Request, call_next):
    # Log the headers for debugging
    logger.info(f"Current header type: {request.headers}")
    logger.info(f"request: {request}")
    
    # Skip validation for health check endpoint
    if request.url.path == "/status" or str(request.url.path).endswith("/status"):
        # Log the health check request
        logger.info(f"Health check request received from {request.client.host}")
        response = await call_next(request)
        return response
    
    # Check for required headers on all other endpoints
    headers = request.headers
    client_type = headers.get("x-client-type")
    auth_header = headers.get("authorization")
    
    logger.info(f"Current client_type: {client_type}")
    logger.info(f"Current auth_header: {auth_header}")
    
    if not client_type:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Missing X-Client-Type header"}
        )
    
    # Make the client_type check case-insensitive
    valid_client_types = ["web", "ios", "android"]
    if client_type.lower() not in valid_client_types:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": f"Invalid X-Client-Type header: {client_type}. Must be one of: Web, iOS, Android"}
        )
    
    if not auth_header:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Missing Authorization header"}
        )
    
    # Continue processing the request if headers are valid
    response = await call_next(request)
    return response

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    # Skip validation for health check endpoint
    if request.url.path == "/status":
        return PlainTextResponse(content="OK", status_code=200)
    
    # Check if the error is due to missing Authorization header
    if any(error["loc"][0] == "header" and error["loc"][1] == "authorization" for error in exc.errors()):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Missing Authorization header"},
        )
    
    # Check if the error is due to missing X-Client-Type header
    if any(error["loc"][0] == "header" and error["loc"][1] == "x_client_type" for error in exc.errors()):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Missing X-Client-Type header"},
        )
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"message": str(exc)},
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail}
    )

async def forward_request(method: str, url: str, headers: dict, **kwargs):
    """
    Forward request to backend service with retries and better error handling
    """
    retry_count = 0
    last_error = None
    logger.info(f" url: {url}")
    logger.info(f"headers: {headers}")
    logger.info(f"kwargs: {kwargs}")
    while retry_count < MAX_RETRIES:
        try:
            # Configure timeouts
            timeout = httpx.Timeout(REQUEST_TIMEOUT, connect=CONNECT_TIMEOUT)
            
            # Log request attempt
            logger.info(f"Forwarding {method} request to {url} (Attempt {retry_count + 1}/{MAX_RETRIES})")
            
            # For POST and PUT requests, handle JSON serialization for Decimal objects
            if method in ["POST", "PUT"] and "json" in kwargs:
                kwargs["content"] = json.dumps(kwargs.pop("json"), cls=CustomJSONEncoder)
                headers = headers.copy() if headers else {}
                headers["Content-Type"] = "application/json"
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(method, url, headers=headers, **kwargs)
                
                # Log response
                logger.info(f"Received {response.status_code} response from {url}")
                
                # Handle 4xx error status codes - pass them through directly
                if 400 <= response.status_code < 500:
                    try:
                        error_detail = response.json().get('message', str(response.content))
                    except Exception:
                        error_detail = str(response.content)
                    
                    logger.info(f"Passing through error response: {response.status_code} - {error_detail}")
                    
                    # Return the original status code and error message
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=error_detail
                    )
                
                # Check for 5xx error status codes
                if response.status_code >= 500:
                    logger.warning(f"Error response from backend: {response.status_code}")
                    try:
                        error_detail = response.json().get('message', str(response.content))
                    except Exception:
                        error_detail = str(response.content)
                        
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=error_detail
                    )
                
                # Parse response for successful requests
                try:
                    json_response = response.json()
                    return response.status_code, json_response
                except Exception as e:
                    logger.error(f"Failed to parse JSON response: {str(e)}")
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Invalid response from backend service"
                    )
                
        except httpx.TimeoutException as e:
            logger.warning(f"Request timed out: {str(e)}")
            last_error = e
        except httpx.NetworkError as e:
            logger.warning(f"Network error: {str(e)}")
            last_error = e
        except httpx.HTTPError as e:
            logger.warning(f"HTTP error: {str(e)}")
            last_error = e
        except HTTPException as e:
            # If it's a HTTPException (like a 404), we want to raise it directly without retrying
            raise e
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            last_error = e
            
        # Increment retry counter
        retry_count += 1
        
        # Wait before retrying
        if retry_count < MAX_RETRIES:
            logger.info(f"Retrying in {RETRY_DELAY} seconds...")
            await asyncio.sleep(RETRY_DELAY)
    
    # If we've exhausted retries, raise an appropriate exception
    if isinstance(last_error, httpx.TimeoutException):
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Backend service timed out after multiple retries"
        )
    elif isinstance(last_error, httpx.NetworkError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to connect to backend service after multiple retries"
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error communicating with backend service: {str(last_error)}"
        )

@app.post("/books", status_code=status.HTTP_201_CREATED)
async def add_book(
    book: Book,
    response: Response,
    x_client_type: str = Header(...),
    authorization: str = Header(...)
):
    # Validate headers
    await validate_client_type(x_client_type)
    await validate_auth(authorization)

    # Convert Decimal values to float for serialization
    book_dict = {
        "ISBN": book.ISBN,
        "title": book.title,
        "Author": book.Author,
        "description": book.description,
        "genre": book.genre,
        "price": float(book.price),
        "quantity": book.quantity
    }

    # Forward request to books service
    status_code, data = await forward_request(
        "POST",
        f"{BOOKS_SERVICE_URL}/books",
        headers={"Authorization": authorization},
        json=book_dict
    )

    # if status_code == 201:
    #     # Set Location header
    #     response.headers["Location"] = f"/books/{book.ISBN}"

    #     # Format response for mobile clients (case-insensitive check)
    #     if x_client_type.lower() in ["ios", "android"] and data["genre"] == "non-fiction":
    #         data["genre"] = "3"

    return data

@app.put("/books/{ISBN}", status_code=status.HTTP_200_OK)
async def update_book(
    ISBN: str,
    book: Book,
    x_client_type: str = Header(...),
    authorization: str = Header(...)
):
    # Validate headers
    await validate_client_type(x_client_type)
    await validate_auth(authorization)

    # Check if ISBNs match between URL and request body
    if ISBN != book.ISBN:
        logger.warning(f"ISBN mismatch: URL has {ISBN}, but request body has {book.ISBN}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "ISBN in URL does not match ISBN in request body"}
        )

    # Convert Decimal values to float for serialization
    book_dict = {
        "ISBN": book.ISBN,
        "title": book.title,
        "Author": book.Author,
        "description": book.description,
        "genre": book.genre,
        "price": float(book.price),
        "quantity": book.quantity
    }

    # Forward request to books service
    status_code, data = await forward_request(
        "PUT",
        f"{BOOKS_SERVICE_URL}/books/{ISBN}",
        headers={"Authorization": authorization},
        json=book_dict
    )

    # if status_code == 200:
    #     # Format response for mobile clients (case-insensitive check)
    #     if x_client_type.lower() in ["ios", "android"] and data["genre"] == "non-fiction":
    #         data["genre"] = "3"

    return data

@app.get("/books/{ISBN}")
@app.get("/books/isbn/{ISBN}")
async def get_book(
    ISBN: str,
    x_client_type: str = Header(...),
    authorization: str = Header(...)
):
    logger.info(f"ISBN: {ISBN}")
    logger.info(f"x_client_type: {x_client_type}")
    logger.info(f"authorization: {authorization}")
    
    # Validate headers
    await validate_client_type(x_client_type)
    await validate_auth(authorization)

    # Forward request to books service
    status_code, data = await forward_request(
        "GET",
        f"{BOOKS_SERVICE_URL}/books/{ISBN}",
        headers={"Authorization": authorization}
    )

    if status_code == 200:
        # Format response for mobile clients (case-insensitive check)
        if x_client_type.lower() in ["ios", "android"] and data["genre"] == "non-fiction":
            # Convert to integer 3 instead of string "3"
            data["genre"] = 3

    return data

@app.post("/customers", status_code=status.HTTP_201_CREATED)
async def add_customer(
    customer: CustomerBase,
    response: Response,
    x_client_type: str = Header(...),
    authorization: str = Header(...)
):
    # Validate headers
    await validate_client_type(x_client_type)
    await validate_auth(authorization)
    
    # Log the request values for debugging
    logger.info(f"Adding customer: {customer.dict()}")
    logger.info(f"Client type: {x_client_type}")

    # Forward request to customers service
    status_code, data = await forward_request(
        "POST",
        f"{CUSTOMERS_SERVICE_URL}/customers",
        headers={"Authorization": authorization},
        json=customer.dict()
    )

    if status_code == 201:
        # Set Location header
        response.headers["Location"] = f"/customers/{data['id']}"

        # Format response for mobile clients (ensure case-insensitive comparison)
        # if x_client_type.lower() in ["ios", "android"]:
        #     logger.info(f"Formatting response for mobile client: {x_client_type}")
        #     # Create a new dictionary with only the fields needed for mobile
        #     mobile_data = {
        #         "id": data["id"],
        #         "userId": data["userId"],
        #         "name": data["name"],
        #         "phone": data["phone"]
        #     }
        #     # Log the mobile data being returned
        #     logger.info(f"Returning mobile data: {mobile_data}")
        #     # Validate against the MobileCustomerResponse model
        #     return mobile_data
        
    return data

@app.get("/customers/{id}", response_model=None)
async def get_customer(
    id: int,
    x_client_type: str = Header(...),
    authorization: str = Header(...)
):
    # Validate headers
    await validate_client_type(x_client_type)
    await validate_auth(authorization)
    
    # Log the request values for debugging
    logger.info(f"Getting customer by id: {id}")
    logger.info(f"Client type: {x_client_type}")

    # Forward request to customers service
    status_code, data = await forward_request(
        "GET",
        f"{CUSTOMERS_SERVICE_URL}/customers/{id}",
        headers={"Authorization": authorization}
    )

    if status_code == 200:
        # Format response for mobile clients (ensure case-insensitive comparison)
        if x_client_type.lower() in ["ios", "android"]:
            logger.info(f"Formatting response for mobile client: {x_client_type}")
            # Create a new dictionary with only the fields needed for mobile
            mobile_data = {
                "id": data["id"],
                "userId": data["userId"],
                "name": data["name"],
                "phone": data["phone"]
            }
            # Log the mobile data being returned
            logger.info(f"Returning mobile data: {mobile_data}")
            return mobile_data
        
    return data

@app.get("/customers", response_model=None)
async def get_customer_by_userId(
    userId: str = Query(..., description="Customer email address (userId)"),
    x_client_type: str = Header(...),
    authorization: str = Header(...)
):
    # Validate headers
    await validate_client_type(x_client_type)
    await validate_auth(authorization)
    
    # Log the request values for debugging
    logger.info(f"Getting customer by userId: {userId}")
    logger.info(f"Client type: {x_client_type}")

    # Forward request to customers service
    status_code, data = await forward_request(
        "GET",
        f"{CUSTOMERS_SERVICE_URL}/customers",
        headers={"Authorization": authorization},
        params={"userId": userId}
    )

    if status_code == 200:
        # Format response for mobile clients (ensure case-insensitive comparison)
        if x_client_type.lower() in ["ios", "android"]:
            logger.info(f"Formatting response for mobile client: {x_client_type}")
            # Create a new dictionary with only the fields needed for mobile
            mobile_data = {
                "id": data["id"],
                "userId": data["userId"],
                "name": data["name"],
                "phone": data["phone"]
            }
            # Log the mobile data being returned
            logger.info(f"Returning mobile data: {mobile_data}")
            return mobile_data
        
    return data