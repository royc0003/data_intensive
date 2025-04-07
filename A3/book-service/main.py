from fastapi import FastAPI, HTTPException, Header, Response, Query, status, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, constr, condecimal, conint, EmailStr, validator, ValidationError
from typing import Optional
import mariadb
import os
import time
from decimal import Decimal
import jwt
from datetime import datetime
import json
from jwt_validator import validate_jwt_token

app = FastAPI()

# JWT validation constants
VALID_SUBJECTS = {"starlord", "gamora", "drax", "rocket", "groot"}
VALID_ISSUER = "cmu.edu"


# Constants for circuit breaker
CIRCUIT_BREAKER_THRESHOLD = 5  # Number of failures before opening circuit
CIRCUIT_BREAKER_TIMEOUT = 60   # Seconds to keep circuit open
CIRCUIT_BREAKER_FILE = "/mnt/circuit/circuit_state.json"
REQUEST_TIMEOUT = 5.0  # Timeout for external service calls in seconds

# Model for related book response
class RelatedBook(BaseModel):
    ISBN: str
    title: str
    Author: str
    

# Determine if this is a BFF service based on port
# IS_BFF_SERVICE = os.getenv("SERVICE_TYPE", "80") == "80"
IS_BFF_SERVICE = False
async def validate_client_type(x_client_type: Optional[str] = Header(None)):
    if IS_BFF_SERVICE:
        if not x_client_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing X-Client-Type header"
            )
        valid_types = {"Web", "iOS", "Android"}
        if x_client_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid X-Client-Type header"
            )
    return x_client_type

# async def validate_auth(authorization: Optional[str] = Header(None)):
#     if IS_BFF_SERVICE:
#         if not authorization:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Missing Authorization header"
#             )
#         validate_jwt_token(authorization)
#     return authorization

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
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
    
    # For other validation errors
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


# MariaDB Connection Configuration
db_config = {
    "host": os.getenv("DB_HOST", "bookstore-db-dev.cluster-csdxv2900nel.us-east-1.rds.amazonaws.com"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "Bookstore"),
    "password": os.getenv("DB_PASSWORD", "password"),
    "database": os.getenv("DB_NAME", "Bookstore"),
    "connect_timeout": 300000,  # 5 minutes connection timeout
    "read_timeout": 300000,     # 5 minutes read timeout
    "write_timeout": 300000     # 5 minutes write timeout
}

def get_db_connection():
    retries = 5
    while retries > 0:
        try:
            connection = mariadb.connect(**db_config)
            connection.autocommit = False
            return connection
        except mariadb.Error as e:
            print(f"Database connection error: {str(e)}")
            retries -= 1
            if retries == 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database connection failed: {str(e)}"
                )
            time.sleep(2)  # Increased sleep time between retries

# Data Model for Validation
class Book(BaseModel):
    ISBN: constr(min_length=10, max_length=20)
    title: str
    Author: str
    description: str
    genre: str
    price: condecimal(gt=0, decimal_places=2)
    quantity: conint(ge=0)

    class Config:
        schema_extra = {
            "example": {
                "ISBN": "978-0321815736",
                "title": "Software Architecture in Practice",
                "Author": "Bass, L.",
                "description": "seminal book on software architecture",
                "genre": "non-fiction",
                "price": 59.95,
                "quantity": 106
            }
        }

class CustomerBase(BaseModel):
    userId: EmailStr
    name: str
    phone: str
    address: str
    address2: Optional[str] = None
    city: str
    state: constr(min_length=2, max_length=2)
    zipcode: str

    @validator('state')
    def validate_state(cls, v):
        valid_states = {
            'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
            'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
            'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
            'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
            'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
        }
        if v.upper() not in valid_states:
            raise ValueError('Invalid US state code')
        return v.upper()

    class Config:
        schema_extra = {
            "example": {
                "userId": "starlord2002@gmail.com",
                "name": "Star Lord",
                "phone": "+14122144122",
                "address": "48 Galaxy Rd",
                "address2": "suite 4",
                "city": "Fargo",
                "state": "ND",
                "zipcode": "58102"
            }
        }

class CustomerResponse(CustomerBase):
    id: int  # Auto-generated unique customer ID

# Add Book Endpoint (Fully Adhering to Requirements)
@app.post("/books", status_code=status.HTTP_201_CREATED)
async def add_book(
    book: Book,
    response: Response,
    x_client_type: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    # Validate headers only for BFF service
    # await validate_client_type(x_client_type)
    # await validate_auth(authorization)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check if ISBN already exists
        cursor.execute("SELECT ISBN FROM Books WHERE ISBN = %s", (book.ISBN,))
        existing_book = cursor.fetchone()
        
        if existing_book:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="This ISBN already exists in the system."
            )

        # Insert the new book
        cursor.execute(
            "INSERT INTO Books (ISBN, title, Author, description, genre, price, quantity) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (book.ISBN, book.title, book.Author, book.description, book.genre, float(book.price), book.quantity)
        )
        conn.commit()

        # Set Location header
        response.headers["Location"] = f"/books/{book.ISBN}"

        return {
            "ISBN": book.ISBN,
            "title": book.title,
            "Author": book.Author,
            "description": book.description,
            "genre": book.genre,
            "price": float(book.price),
            "quantity": book.quantity
        }

    except HTTPException as e:
        raise e
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(err)
        )
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.put("/books/{ISBN}", status_code=status.HTTP_200_OK)
async def update_book(
    ISBN: str,
    book: Book,
    x_client_type: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    # Validate headers only for BFF service
    # await validate_client_type(x_client_type)
    # await validate_auth(authorization)

    # Check if ISBNs match
    if ISBN != book.ISBN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ISBN in URL does not match ISBN in request body"
        )

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check if book exists
        cursor.execute("SELECT * FROM Books WHERE ISBN = %s", (ISBN,))
        existing_book = cursor.fetchone()

        if not existing_book:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

        cursor.execute(
            """UPDATE Books 
               SET title = %s, Author = %s, description = %s, genre = %s, price = %s, quantity = %s
               WHERE ISBN = %s""",
            (book.title, book.Author, book.description, book.genre, float(book.price), book.quantity, ISBN)
        )
        conn.commit()

        return {
            "ISBN": ISBN,
            "title": book.title,
            "Author": book.Author,
            "description": book.description,
            "genre": book.genre,
            "price": float(book.price),
            "quantity": book.quantity
        }

    except HTTPException as e:
        raise e
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(err)
        )
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.get("/books/{ISBN}")
@app.get("/books/isbn/{ISBN}")
async def get_book(
    ISBN: str,
    x_client_type: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    # Validate headers only for BFF service
    # await validate_client_type(x_client_type)
    # await validate_auth(authorization)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch book from database
        cursor.execute("SELECT * FROM Books WHERE ISBN = %s", (ISBN,))
        book = cursor.fetchone()

        if not book:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

        # Handle mobile app specific requirement for BFF service
        # if IS_BFF_SERVICE and x_client_type in ["iOS", "Android"]:
        #     if book["genre"] == "non-fiction":
        #         book["genre"] = "3"

        return book

    except HTTPException as e:
        raise e
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(err)
        )
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()


# Related books endpoint
@app.get("/books/{ISBN}/related-books", response_model=List[RelatedBook])
async def get_related_books(
    ISBN: str,
    response: Response,
    x_client_type: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    # Check circuit breaker state
    # if not await circuit_breaker.check_state():
    #     raise HTTPException(
    #         status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    #         detail="Service temporarily unavailable due to circuit breaker"
    #     )

    # External service URL (replace with actual URL from Canvas)
    RECOMMENDATION_SERVICE_URL = os.getenv(
        "RECOMMENDATION_SERVICE_URL", 
        "http://recommendation-service:8080"
    )
    
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            # Make request to recommendation service
            response = await client.get(
                f"{RECOMMENDATION_SERVICE_URL}/recommendations/{ISBN}"
            )

            # Handle different response scenarios
            if response.status_code == 200:
                # Record successful call
                # await circuit_breaker.record_success()
                
                # Parse and return recommendations
                recommendations = response.json()
                if not recommendations:
                    response.status_code = status.HTTP_204_NO_CONTENT
                    return []
                return recommendations

            elif response.status_code == 404:
                # ISBN not found
                response.status_code = status.HTTP_204_NO_CONTENT
                return []

            else:
                # Handle unexpected response
                # await circuit_breaker.record_failure()
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Unexpected response from recommendation service"
                )

    except httpx.TimeoutException:
        # Handle timeout
        # await circuit_breaker.record_failure()
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Recommendation service timed out"
        )
    
    except Exception as e:
        # Handle other errors
        # await circuit_breaker.record_failure()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error accessing recommendation service: {str(e)}"
        )

@app.post("/customers", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def add_customer(
    customer: CustomerBase,
    response: Response,
    x_client_type: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    # Validate headers only for BFF service
    # await validate_client_type(x_client_type)
    # await validate_auth(authorization)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check if userId already exists
        cursor.execute("SELECT id FROM Customers WHERE userId = %s", (customer.userId,))
        existing_customer = cursor.fetchone()

        if existing_customer:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="This user ID already exists in the system."
            )

        # Insert new customer
        cursor.execute(
            """INSERT INTO Customers (userId, name, phone, address, address2, city, state, zipcode)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (customer.userId, customer.name, customer.phone, customer.address, 
             customer.address2, customer.city, customer.state, customer.zipcode)
        )
        conn.commit()

        new_id = cursor.lastrowid

        # Set Location header
        response.headers["Location"] = f"/customers/{new_id}"

        # Return the customer data directly
        return {
            "id": new_id,
            "userId": customer.userId,
            "name": customer.name,
            "phone": customer.phone,
            "address": customer.address,
            "address2": customer.address2,
            "city": customer.city,
            "state": customer.state,
            "zipcode": customer.zipcode
        }

    except HTTPException as e:
        raise e
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(err)
        )
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.get("/customers/{id}", response_model=CustomerResponse)
async def get_customer(
    id: int,
    x_client_type: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    # Validate headers only for BFF service
    # await validate_client_type(x_client_type)
    # await validate_auth(authorization)

    try:
        if id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid customer ID"
            )

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch customer from database
        cursor.execute("SELECT * FROM Customers WHERE id = %s", (id,))
        customer = cursor.fetchone()

        if not customer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")


        return customer

    except HTTPException as e:
        raise e
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(err)
        )
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.get("/customers", response_model=CustomerResponse)
async def get_customer_by_userId(
    userId: str = Query(..., description="Customer email address (userId)"),
    x_client_type: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    # Validate headers only for BFF service
    # await validate_client_type(x_client_type)
    # await validate_auth(authorization)

    # Validate email format
    if '@' not in userId or '.' not in userId or ' ' in userId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM Customers WHERE userId = %s", (userId,))
        customer = cursor.fetchone()

        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )

        return customer

    except HTTPException as e:
        raise e
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(err)
        )
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.get("/status", response_model=str)
def health_check():
    return "OK"