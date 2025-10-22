
-- Drop the database if it exists (for a clean start)
DROP DATABASE IF EXISTS ArchitectureDB;

-- Create a fresh database
CREATE DATABASE ArchitectureDB;
USE ArchitectureDB;

-- Address table
CREATE TABLE IF NOT EXISTS Address (
    address_id INT AUTO_INCREMENT PRIMARY KEY,
    street_address VARCHAR(100),
    city VARCHAR(50),
    state VARCHAR(50),
    street_number VARCHAR(10),
    postal_code VARCHAR(20),
    country VARCHAR(50)
);

-- Project table
CREATE TABLE IF NOT EXISTS Project (
    project_number INT AUTO_INCREMENT PRIMARY KEY,
    address_id INT,
    client VARCHAR(100),
    client_phone VARCHAR(20),
    client_email VARCHAR(100),
    size ENUM('S', 'M', 'L'),
    start_date DATE,
    last_interaction_date DATE,
    employee_creator VARCHAR(100),
    FOREIGN KEY (address_id) REFERENCES Address(address_id),
    M1 INT default 0,
    M2 INT default 0,
    M3 INT default 0
);

-- Sample address data
INSERT INTO Address (street_address, city, state, street_number, postal_code, country)
VALUES 
('Main St', 'Springfield', 'IL', '123', '62701', 'USA'),
('Oak Ave', 'Chicago', 'IL', '456', '60616', 'USA'),
('Pine Rd', 'Naperville', 'IL', '789', '60540', 'USA');

-- Sample project data
INSERT INTO Project (address_id, client, client_phone, client_email, size, start_date, last_interaction_date, employee_creator)
VALUES 
(1, 'John Smith', '555-1234', 'john.smith@email.com', 'M', '2025-10-01', '2025-10-10', 'Edwin');

-- Verify results
SELECT * FROM Address;
SELECT * FROM Project;



'''
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
'''