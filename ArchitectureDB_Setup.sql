-- Drop the database if it exists (Refresh/Clean start)
DROP DATABASE IF EXISTS ArchitectureDB;

-- Create a fresh database
CREATE DATABASE ArchitectureDB;
USE ArchitectureDB;

-- Address table
CREATE TABLE IF NOT EXISTS Address (
    address_id INT AUTO_INCREMENT PRIMARY KEY,
    street_number VARCHAR(10),
    street_name VARCHAR(100),
    city VARCHAR(50),
    state VARCHAR(50),
    postal_code VARCHAR(20),
    country VARCHAR(50)
);

-- New project table
CREATE TABLE IF NOT EXISTS Project (
	project_number INT AUTO_INCREMENT PRIMARY KEY,
    address_id INT,
    client VARCHAR(100),
    size ENUM('S', 'M', 'L'),
    start_date DATE,
    last_interaction_date DATE,
    employee_creator VARCHAR(100),
    FOREIGN KEY (address_id) REFERENCES Address(address_id)
);

-- Sample addresses (for testing, can remove later)
INSERT INTO Address (street_number, street_name, city, state, postal_code, country)
VALUES 
('123', 'Main St', 'Springfield', 'IL', '62701', 'USA'),
('456', 'Oak Ave', 'Chicago', 'IL', '60616', 'USA'),
('789', 'Pine Rd', 'Naperville', 'IL', '60540', 'USA');

-- Test insert for project table (linked to Address)
INSERT INTO Project (address_id, client, size, start_date, last_interaction_date, employee_creator)
VALUES (1, 'John Smith', 'M', '2025-10-01', '2025-10-10', 'Edwin');

-- Check all addresses
SELECT * FROM Address;

-- Check all projects
SELECT * FROM Project;