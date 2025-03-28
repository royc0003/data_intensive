#!/bin/bash

# Check if required environment variables are set
if [ -z "$DB_HOST" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ]; then
    echo "Error: Required environment variables not set"
    echo "Please set DB_HOST, DB_USER, and DB_PASSWORD"
    exit 1
fi

# Execute SQL script
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" < init_db.sql 