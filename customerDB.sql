-- Drop the database if it exists (Refresh/Clean start)
DROP DATABASE IF EXISTS CustomerDB;

-- Create a fresh database
CREATE DATABASE CustomerDB;
USE CustomerDB;

-- Create Customer table
CREATE TABLE IF NOT EXISTS Customer (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(20),
    address VARCHAR(255)
);

-- Sample insert into Customer table
INSERT INTO Customer (name, email, phone, address)
VALUES ('John Doe', 'john@example.com', '1234567890', '123 Main St');

-- View all customers
SELECT * FROM Customer;
