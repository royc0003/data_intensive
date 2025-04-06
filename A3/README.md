# Bookstore Microservices

This project implements a bookstore system using microservices architecture with FastAPI. The system consists of three main services:

1. Books Service - Handles book-related operations
2. Customers Service - Handles customer-related operations
3. BFF (Backend for Frontend) Service - Handles client-specific formatting and routing

## Architecture

- Books Service (Port 3000)
  - Handles CRUD operations for books
  - Direct database access
  - No client-specific formatting

- Customers Service (Port 3001)
  - Handles CRUD operations for customers
  - Direct database access
  - No client-specific formatting

- BFF Service (Port 80)
  - Routes requests to appropriate backend services
  - Handles client-specific formatting
  - Validates JWT tokens and client types
  - Supports Web, iOS, and Android clients

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
export DB_HOST=your_db_host
export DB_PORT=3306
export DB_USER=Bookstore
export DB_PASSWORD=your_password
export DB_NAME=Bookstore
export SERVICE_TYPE=80  # For BFF service
export BOOKS_SERVICE_URL=http://localhost:3000
export CUSTOMERS_SERVICE_URL=http://localhost:3001
```

## Running the Services

1. Start the Books Service:
```bash
uvicorn services.books.main:app --host 0.0.0.0 --port 3000
```

2. Start the Customers Service:
```bash
uvicorn services.customers.main:app --host 0.0.0.0 --port 3001
```

3. Start the BFF Service:
```bash
uvicorn services.bff.main:app --host 0.0.0.0 --port 80
```

## API Documentation

Once the services are running, you can access the API documentation at:
- Books Service: http://localhost:3000/docs
- Customers Service: http://localhost:3001/docs
- BFF Service: http://localhost/docs

## Authentication

All requests to the BFF service must include:
1. `Authorization` header with a valid JWT token
2. `X-Client-Type` header with one of: "Web", "iOS", or "Android"

## Client-Specific Formatting

### Mobile Clients (iOS/Android)
- Book genre "non-fiction" is converted to "3"
- Customer address fields are removed from responses

### Web Client
- No special formatting is applied
- All fields are returned as-is

## Error Handling

- 400 Bad Request: Invalid request format or missing X-Client-Type header
- 401 Unauthorized: Missing or invalid JWT token
- 404 Not Found: Resource not found
- 422 Unprocessable Entity: Duplicate ISBN or userId
- 500 Internal Server Error: Database or service errors 