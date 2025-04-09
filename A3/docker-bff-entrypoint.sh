#!/bin/bash

# Function to wait for MySQL
# wait_for_mysql() {
#     echo "Waiting for MySQL to be ready..."
#     local retries=5
#     while [ $retries -gt 0 ]; do
#         if nc -z $DB_HOST 3306; then
#             echo "MySQL is ready!"
#             return 0
#         fi
#         echo "MySQL not ready yet, retrying... ($retries attempts left)"
#         retries=$((retries-1))
#         sleep 1
#     done
#     echo "Could not connect to MySQL after 30 seconds"
#     return 1
# }

# Function to wait for a backend service
wait_for_backend() {
    local service_url=localhost:3000
    local service_name=$2
    echo "Waiting for $service_name to be ready..."
    local retries=1
    while [ $retries -gt 0 ]; do
        if curl -s -f "${service_url}/status" > /dev/null 2>&1; then
            echo "$service_name is ready!"
            return 0
        fi
        echo "$service_name not ready yet, retrying... ($retries attempts left)"
        retries=$((retries-1))
        sleep 2
    done
    echo "Could not connect to $service_name after multiple attempts. Proceeding anyway..."
    return 0  # Continue anyway to avoid blocking startup
}

# Wait for MySQL to be ready
# if ! wait_for_mysql; then
#     echo "Failed to connect to MySQL. Exiting..."
#     exit 1
# fi

# Wait for backend services (but don't block completely if they're not ready)
# wait_for_backend "$BOOKS_SERVICE_URL" "Books Service"
# wait_for_backend "$CUSTOMERS_SERVICE_URL" "Customers Service"

echo "Starting BFF service on port 80..."

# Use UVICORN_LOG_LEVEL to control logging verbosity
export UVICORN_LOG_LEVEL=${UVICORN_LOG_LEVEL:-info}

# Set higher timeouts for the BFF service
# exec uvicorn services.bff.main:app --host 0.0.0.0 --port 80 --workers 4 --timeout-keep-alive 75 --log-level $UVICORN_LOG_LEVEL
exec uvicorn main:app --host 0.0.0.0 --port 8080 --workers 4 --timeout-keep-alive 75 --log-level $UVICORN_LOG_LEVEL