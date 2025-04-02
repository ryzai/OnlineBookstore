-- Create the database
CREATE DATABASE IF NOT EXISTS online_bookstore;
USE online_bookstore;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    address TEXT,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Books table
CREATE TABLE IF NOT EXISTS books (
    book_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(100) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    genre VARCHAR(50),
    stock_quantity INT NOT NULL DEFAULT 0,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'Processing',
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Order items table (junction table)
CREATE TABLE IF NOT EXISTS order_items (
    order_id INT NOT NULL,
    book_id INT NOT NULL,
    quantity INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    PRIMARY KEY (order_id, book_id),
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE CASCADE
);

-- Shopping cart table
CREATE TABLE IF NOT EXISTS shopping_cart (
    cart_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    book_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE CASCADE,
    UNIQUE KEY (user_id, book_id)
);

-- Insert sample admin user (password: admin123)
INSERT INTO users (name, email, password, is_admin) VALUES 
('Admin User', 'admin@bookstore.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', TRUE);

-- Insert sample customer user (password: customer123)
INSERT INTO users (name, email, password, address) VALUES 
('John Customer', 'customer@example.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', '123 Main St, Anytown, USA');

-- Insert sample books
INSERT INTO books (title, author, price, genre, stock_quantity, description) VALUES 
('The Great Gatsby', 'F. Scott Fitzgerald', 12.99, 'Classic', 50, 'A story of wealth, love, and the American Dream in the 1920s.'),
('To Kill a Mockingbird', 'Harper Lee', 10.99, 'Fiction', 30, 'A powerful story of racial injustice and moral growth.'),
('1984', 'George Orwell', 9.99, 'Dystopian', 25, 'A dystopian novel about totalitarianism and surveillance.'),
('Pride and Prejudice', 'Jane Austen', 8.99, 'Romance', 40, 'A romantic novel about the Bennett family.'),
('The Hobbit', 'J.R.R. Tolkien', 14.99, 'Fantasy', 35, 'A fantasy novel about Bilbo Baggins and his adventure.');

-- Sample order data
INSERT INTO orders (user_id, total_amount, status) VALUES 
(2, 32.97, 'Completed');

INSERT INTO order_items (order_id, book_id, quantity, price) VALUES 
(1, 1, 1, 12.99),
(1, 2, 1, 10.99),
(1, 3, 1, 9.99);