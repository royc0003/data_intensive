from fastapi import FastAPI, HTTPException, Header, Response, Query, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from typing import Optional
from ..shared.models import CustomerBase, CustomerResponse
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

@app.post("/customers", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def add_customer(
    customer: CustomerBase,
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
    await validate_client_type(x_client_type)
    await validate_auth(authorization)

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
    await validate_client_type(x_client_type)
    await validate_auth(authorization)

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
async def health_check(
    x_client_type: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    # Validate headers only for BFF service
    await validate_client_type(x_client_type)
    await validate_auth(authorization)
    return "OK" 