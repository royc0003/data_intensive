from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, constr, condecimal, conint
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
    author: str
    description: str
    genre: str
    price: condecimal(gt=0, decimal_places=2)  # Enforces price > 0 with 2 decimal places
    quantity: conint(ge=0)  # Ensures quantity is a non-negative integer

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
            "INSERT INTO Books (ISBN, title, author, description, genre, price, quantity) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (book.ISBN, book.title, book.author, book.description, book.genre, book.price, book.quantity)
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
        "author": book.author,
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
               SET title = %s, author = %s, description = %s, genre = %s, price = %s, quantity = %s
               WHERE ISBN = %s""",
            (book.title, book.author, book.description, book.genre, book.price, book.quantity, ISBN)
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
        "author": book.author,
        "description": book.description,
        "genre": book.genre,
        "price": book.price,
        "quantity": book.quantity
    }