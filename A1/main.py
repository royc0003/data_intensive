from fastapi import FastAPI, HTTPException, Header, Response, Query, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, constr, condecimal, conint, EmailStr, validator, ValidationError
from typing import Optional
import mariadb
import os
import time
from decimal import Decimal

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    if any(error["type"] == "value_error.missing" for error in exc.errors()):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Missing required fields"},
        )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )

# MariaDB Connection Configuration
db_config = {
    "host": os.getenv("DB_HOST", "bookstore-db-dev.cluster-cnomgymiqut0.us-east-1.rds.amazonaws.com"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "Bookstore"),
    "password": os.getenv("DB_PASSWORD", "password"),
    "database": os.getenv("DB_NAME", "Bookstore"),
    "connect_timeout": 100000
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
            time.sleep(1)

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
async def add_book(book: Book, response: Response):
    try:
        conn = get_db_connection()
    except HTTPException as e:
        # Re-raise database connection errors
        raise e

    try:
        cursor = conn.cursor(dictionary=True)

        # Check if ISBN already exists
        cursor.execute("SELECT ISBN FROM Books WHERE ISBN = %s", (book.ISBN,))
        existing_book = cursor.fetchone()
        
        if existing_book:
            cursor.close()
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"message": "This ISBN already exists in the system."}
            )

        # Insert the new book
        cursor.execute(
            "INSERT INTO Books (ISBN, title, Author, description, genre, price, quantity) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (book.ISBN, book.title, book.Author, book.description, book.genre, float(book.price), book.quantity)
        )
        conn.commit()
        
        cursor.close()
        conn.close()

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

    except mariadb.Error as err:
        if conn:
            conn.rollback()
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    except Exception as err:
        if conn:
            conn.rollback()
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err))


@app.put("/books/{ISBN}", status_code=status.HTTP_200_OK)
async def update_book(ISBN: str, book: Book):
    # Check if ISBNs match
    if ISBN != book.ISBN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ISBN in URL does not match ISBN in request body"
        )

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Check if book exists
    cursor.execute("SELECT * FROM Books WHERE ISBN = %s", (ISBN,))
    existing_book = cursor.fetchone()

    if not existing_book:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    try:
        cursor.execute(
            """UPDATE Books 
               SET title = %s, Author = %s, description = %s, genre = %s, price = %s, quantity = %s
               WHERE ISBN = %s""",
            (book.title, book.Author, book.description, book.genre, float(book.price), book.quantity, ISBN)
        )
        conn.commit()
    except mariadb.Error as err:
        conn.rollback()
        cursor.close()
        conn.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    cursor.close()
    conn.close()

    return {
        "ISBN": ISBN,
        "title": book.title,
        "Author": book.Author,
        "description": book.description,
        "genre": book.genre,
        "price": float(book.price),
        "quantity": book.quantity
    }

@app.get("/books/{ISBN}")
@app.get("/books/isbn/{ISBN}")
def get_book(ISBN: str):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch book from database
    cursor.execute("SELECT * FROM Books WHERE ISBN = %s", (ISBN,))
    book = cursor.fetchone()

    cursor.close()
    conn.close()

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    return book


@app.post("/customers", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def add_customer(customer: CustomerBase, response: Response):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Check if userId already exists
            cursor.execute("SELECT id FROM Customers WHERE userId = %s", (customer.userId,))
            existing_customer = cursor.fetchone()

            if existing_customer:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={"message": "This user ID already exists in the system."}
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

            # Fetch the newly created customer to ensure we return the exact database state
            cursor.execute("SELECT * FROM Customers WHERE id = %s", (new_id,))
            new_customer = cursor.fetchone()

            return new_customer

        finally:
            cursor.close()
            conn.close()

    except HTTPException as e:
        raise e
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": str(err)}  # Wrap error message in correct format
        )

@app.get("/customers/{id}", response_model=CustomerResponse)
def get_customer(id: int):
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

        cursor.close()
        conn.close()

        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        return customer
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid customer ID format"
        )

@app.get("/customers", response_model=CustomerResponse)
def get_customer_by_userId(userId: str = Query(..., description="Customer email address (userId)")):
    # Validate email format
    if '@' not in userId or '.' not in userId or ' ' in userId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Invalid email format"}
        )

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("SELECT * FROM Customers WHERE userId = %s", (userId,))
            customer = cursor.fetchone()

            if not customer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"message": "Customer not found"}
                )

            return customer

        finally:
            cursor.close()
            conn.close()

    except HTTPException as e:
        raise e
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": str(err)}
        )

@app.get("/status", response_model=str)
def health_check():
    return "OK"