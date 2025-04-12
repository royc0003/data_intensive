import os
import mariadb
import time
from fastapi import HTTPException, status

# JWT validation constants
VALID_SUBJECTS = {"starlord", "gamora", "drax", "rocket", "groot"}
VALID_ISSUER = "cmu.edu"

# Determine if this is a BFF service based on port
IS_BFF_SERVICE = os.getenv("SERVICE_TYPE", "80") == "80"

# MariaDB Connection Configuration
db_config = {
    "host": os.getenv("DB_HOST", "bookstore-db-dev.cluster-csdxv2900nel.us-east-1.rds.amazonaws.com"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "Bookstore"),
    "password": os.getenv("DB_PASSWORD", "password"),
    "database": os.getenv("DB_NAME", "Bookstore"),
    "connect_timeout": 100000
}

def get_db_connection():
    retries = 5
    while retries > 0:
        try:
            connection = mariadb.connect(**db_config)
            connection.autocommit = False
            return connection
        except mariadb.Error as e:
            print(f"Database connection error: {str(e)}")
            retries -= 1
            if retries == 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database connection failed: {str(e)}"
                )
            time.sleep(1) 