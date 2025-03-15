from fastapi import FastAPI, HTTPException
import mysql.connector

app = FastAPI()

# MySQL Database Connection (Local)
db_config = {
    "host": "127.0.0.1",  # Use "localhost" or "127.0.0.1"
    "user": "root",
    "password": "yourpassword",
    "database": "Bookstore"
}

# Function to Connect to MySQL
def get_db_connection():
    return mysql.connector.connect(**db_config)

# Health Check Endpoint
@app.get("/status")
def health_check():
    try:
        conn = get_db_connection()
        conn.ping(reconnect=True)
        conn.close()
        return {"status": "OK"}
    except Exception as e:
        return {"status": "Error", "message": str(e)}

# Endpoint to Retrieve All Books
@app.get("/books")
def get_books():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Books")
    books = cursor.fetchall()
    cursor.close()
    conn.close()
    return {"books": books}

# Endpoint to Add a Book
@app.post("/books")
def add_book(book: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO Books (ISBN, title, author, description, genre, price, quantity) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (book["ISBN"], book["title"], book["author"], book["description"], book["genre"], book["price"], book["quantity"])
        )
        conn.commit()
    except mysql.connector.Error as err:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(err))
    finally:
        cursor.close()
        conn.close()
    return {"message": "Book added successfully"}

# Start FastAPI server (run `uvicorn main:app --reload`)
