from fastapi import FastAPI, HTTPException, Header, Response
from pydantic import BaseModel, constr, condecimal, conint, EmailStr
import mysql.connector

app = FastAPI()

# MySQL Database Connection (Local)
db_config = {
    "host": "127.0.0.1",  # Use "localhost" or "127.0.0.1"
    "user": "root",
    "password": "password",
    "database": "Bookstore"
}

# Function to Connect to MySQL
def get_db_connection():
    return mysql.connector.connect(**db_config)

# Data Model for Validation
class Book(BaseModel):
    ISBN: constr(min_length=10, max_length=20)  # ISBN is a string (10-20 chars)
    title: str
    Author: str
    description: str
    genre: str
    price: condecimal(gt=0, decimal_places=2)  # Enforces price > 0 with 2 decimal places
    quantity: conint(ge=0)  # Ensures quantity is a non-negative integer

class CustomerBase(BaseModel):
    userId: EmailStr  # Ensures userId is a valid email
    name: str
    phone: str
    address: str
    address2: str | None = None  # Optional field
    city: str
    state: constr(min_length=2, max_length=2)  # Ensures state is exactly 2 letters
    zipcode: str
    
class CustomerResponse(CustomerBase):
    id: int  # Auto-generated unique customer ID

# Add Book Endpoint (Fully Adhering to Requirements)
@app.post("/books", status_code=201)
def add_book(book: Book):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Check if ISBN already exists
    cursor.execute("SELECT ISBN FROM Books WHERE ISBN = %s", (book.ISBN,))
    existing_book = cursor.fetchone()
    
    if existing_book:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=422, detail={"message": "This ISBN already exists in the system."})

    try:
        # Insert the new book
        cursor.execute(
            "INSERT INTO Books (ISBN, title, Author, description, genre, price, quantity) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (book.ISBN, book.title, book.Author, book.description, book.genre, book.price, book.quantity)
        )
        conn.commit()
    except mysql.connector.Error as err:
        conn.rollback()
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail=str(err))
    
    cursor.close()
    conn.close()

    # Return success response with location header
    return {
        "ISBN": book.ISBN,
        "title": book.title,
        "Author": book.Author,
        "description": book.description,
        "genre": book.genre,
        "price": book.price,
        "quantity": book.quantity
    }, {"Location": f"/books/{book.ISBN}"}


@app.put("/books/{ISBN}", status_code=200)
def update_book(ISBN: str, book: Book):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Check if book exists
    cursor.execute("SELECT * FROM Books WHERE ISBN = %s", (ISBN,))
    existing_book = cursor.fetchone()

    if not existing_book:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Book not found")

    try:
        # Update book details
        cursor.execute(
            """UPDATE Books 
               SET title = %s, Author = %s, description = %s, genre = %s, price = %s, quantity = %s
               WHERE ISBN = %s""",
            (book.title, book.Author, book.description, book.genre, book.price, book.quantity, ISBN)
        )
        conn.commit()
    except mysql.connector.Error as err:
        conn.rollback()
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail=str(err))

    cursor.close()
    conn.close()

    return {
        "ISBN": ISBN,
        "title": book.title,
        "Author": book.Author,
        "description": book.description,
        "genre": book.genre,
        "price": book.price,
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


@app.post("/customers", response_model=CustomerResponse, status_code=201)
def add_customer(customer: CustomerBase, response: Response):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Check if userId already exists
    cursor.execute("SELECT id FROM Customers WHERE userId = %s", (customer.userId,))
    existing_customer = cursor.fetchone()

    if existing_customer:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=422, detail={"message": "This user ID already exists in the system."})

    try:
        # Insert new customer and retrieve auto-generated ID
        cursor.execute(
            """INSERT INTO Customers (userId, name, phone, address, address2, city, state, zipcode)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (customer.userId, customer.name, customer.phone, customer.address, customer.address2,
             customer.city, customer.state, customer.zipcode)
        )
        conn.commit()

        # Get the auto-incremented customer ID
        customer_id = cursor.lastrowid

    except mysql.connector.Error as err:
        conn.rollback()
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail=str(err))

    cursor.close()
    conn.close()

    # Set Location header
    response.headers["Location"] = f"/customers/{customer_id}"

    return CustomerResponse(id=customer_id, **customer.dict())

@app.get("/customers/{id}", response_model=CustomerResponse)
def get_customer(id: int):
    if id <= 0:
        raise HTTPException(status_code=400, detail="Invalid customer ID")

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