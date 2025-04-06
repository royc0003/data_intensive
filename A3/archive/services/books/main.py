from fastapi import FastAPI, HTTPException, Header, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from typing import Optional
from ..shared.models import Book
from ..shared.utils import get_db_connection
from ..shared.auth import validate_client_type, validate_auth

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
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

@app.post("/books", status_code=status.HTTP_201_CREATED)
async def add_book(
    book: Book,
    response: Response,
    x_client_type: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    # Validate headers only for BFF service
    await validate_client_type(x_client_type)
    await validate_auth(authorization)

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
    await validate_client_type(x_client_type)
    await validate_auth(authorization)

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
    await validate_client_type(x_client_type)
    await validate_auth(authorization)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch book from database
        cursor.execute("SELECT * FROM Books WHERE ISBN = %s", (ISBN,))
        book = cursor.fetchone()

        if not book:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

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

@app.get("/status", response_model=str)
async def health_check(
    x_client_type: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    # Validate headers only for BFF service
    await validate_client_type(x_client_type)
    await validate_auth(authorization)
    return "OK" 