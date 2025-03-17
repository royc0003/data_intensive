#!/bin/bash

# Function to wait for MySQL
wait_for_mysql() {
    echo "Waiting for MySQL to be ready..."
    local retries=30
    while [ $retries -gt 0 ]; do
        if nc -z $DB_HOST 3306; then
            echo "MySQL is ready!"
            return 0
        fi
        echo "MySQL not ready yet, retrying... ($retries attempts left)"
        retries=$((retries-1))
        sleep 1
    done
    echo "Could not connect to MySQL after 30 seconds"
    return 1
}

# Wait for MySQL to be ready
if ! wait_for_mysql; then
    echo "Failed to connect to MySQL. Exiting..."
    exit 1
fi

# Start the application
exec uvicorn main:app --host 0.0.0.0 --port 8000 