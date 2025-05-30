CREATE DATABASE IF NOT EXISTS Bookstore;
USE Bookstore;

-- Drop existing tables if they exist
DROP TABLE IF EXISTS Books;
DROP TABLE IF EXISTS Customers;

CREATE TABLE IF NOT EXISTS Books (
    ISBN VARCHAR(20) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    Author VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    genre VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL CHECK (price >= 0),
    quantity INT NOT NULL CHECK (quantity >= 0)
);

CREATE TABLE IF NOT EXISTS Customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    userId VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    address VARCHAR(255) NOT NULL,
    address2 VARCHAR(255) NULL,
    city VARCHAR(100) NOT NULL,
    state CHAR(2) NOT NULL,
    zipcode VARCHAR(10) NOT NULL
); 