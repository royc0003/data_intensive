#!/bin/bash

# Function to wait for MySQL
# wait_for_mysql() {
#     echo "Waiting for MySQL to be ready..."
#     local retries=30
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

# Function to wait for a service
wait_for_service() {
    local service_url=$1
    local service_name=$2
    echo "Waiting for $service_name to be ready..."
    local retries=2
    while [ $retries -gt 0 ]; do
        if curl -f "$service_url/status" >/dev/null 2>&1; then
            echo "$service_name is ready!"
            return 0
        fi
        echo "$service_name not ready yet, retrying... ($retries attempts left)"
        retries=$((retries-1))
        sleep 1
    done
    echo "Could not connect to $service_name after 30 seconds"
    return 1
}

# Wait for MySQL to be ready
# if ! wait_for_mysql; then
#     echo "Failed to connect to MySQL. Exiting..."
#     exit 1
# fi
PORT=3000
# Determine which port to use based on SERVICE_TYPE environment variable
PORT=${SERVICE_TYPE:-80}

# Set appropriate number of workers
if [ "${PORT}" = "80" ]; then
    # BFF service handles more concurrent requests
    WORKERS=4
else
    # Backend services are more DB intensive
    WORKERS=2
fi

echo "Starting service on port $PORT with $WORKERS workers"
exec uvicorn main:app --host 0.0.0.0 --port 3000 --workers $WORKERS --timeout-keep-alive 75