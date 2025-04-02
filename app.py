from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

# SQL configuration for Render
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', '').replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# User Model
class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    address = db.Column(db.Text)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Book Model
class Book(db.Model):
    __tablename__ = 'books'
    book_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    genre = db.Column(db.String(50))
    stock_quantity = db.Column(db.Integer, default=0)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Order Model
class Order(db.Model):
    __tablename__ = 'orders'
    order_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), default='Processing')
    user = db.relationship('User', backref='orders')

# Order Item Model
class OrderItem(db.Model):
    __tablename__ = 'order_items'
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id', ondelete='CASCADE'), primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.book_id', ondelete='CASCADE'), primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    book = db.relationship('Book')

# Shopping Cart Model
class ShoppingCart(db.Model):
    __tablename__ = 'shopping_cart'
    cart_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.book_id', ondelete='CASCADE'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    user = db.relationship('User', backref='cart_items')
    book = db.relationship('Book')
    __table_args__ = (db.UniqueConstraint('user_id', 'book_id'),)
# ========================
# Frontend Routes
# ========================

@app.route('/')
def home():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM books LIMIT 4")
    featured_books = cursor.fetchall()
    cursor.close()
    return render_template('index.html', featured_books=featured_books)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
    
@app.route('/books')
def book_list():
    search_query = request.args.get('q', '')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if search_query:
        cursor.execute("""
            SELECT * FROM books 
            WHERE title LIKE %s OR author LIKE %s OR genre LIKE %s
        """, (f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"))
    else:
        cursor.execute("SELECT * FROM books")
    
    all_books = cursor.fetchall()
    cursor.close()
    return render_template('books.html', books=all_books, search_query=search_query)

@app.route('/book/<int:book_id>')
def book_detail(book_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM books WHERE book_id = %s", (book_id,))
    book = cursor.fetchone()
    cursor.close()
    
    if not book:
        flash('Book not found', 'danger')
        return redirect(url_for('book_list'))
    
    return render_template('book_detail.html', book=book)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        flash('Please login to add items to cart', 'danger')
        return redirect(url_for('login'))
    
    book_id = request.form.get('book_id')
    quantity = int(request.form.get('quantity', 1))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Check if book exists and has sufficient stock
    cursor.execute("SELECT * FROM books WHERE book_id = %s", (book_id,))
    book = cursor.fetchone()
    
    if not book or book['stock_quantity'] < quantity:
        flash('Book not available in requested quantity', 'danger')
        return redirect(url_for('book_detail', book_id=book_id))
    
    # Check if book already in cart
    cursor.execute("""
        SELECT * FROM shopping_cart 
        WHERE user_id = %s AND book_id = %s
    """, (session['user_id'], book_id))
    existing_item = cursor.fetchone()
    
    if existing_item:
        new_quantity = existing_item['quantity'] + quantity
        cursor.execute("""
            UPDATE shopping_cart 
            SET quantity = %s 
            WHERE cart_id = %s
        """, (new_quantity, existing_item['cart_id']))
    else:
        cursor.execute("""
            INSERT INTO shopping_cart (user_id, book_id, quantity)
            VALUES (%s, %s, %s)
        """, (session['user_id'], book_id, quantity))
    
    mysql.connection.commit()
    cursor.close()
    
    flash('Book added to cart successfully', 'success')
    return redirect(url_for('view_cart'))

@app.route('/cart')
def view_cart():
    if 'user_id' not in session:
        flash('Please login to view your cart', 'danger')
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # JOIN operation between shopping_cart and books tables
    cursor.execute("""
        SELECT sc.cart_id, sc.quantity, 
               b.book_id, b.title, b.author, b.price, b.stock_quantity
        FROM shopping_cart sc
        JOIN books b ON sc.book_id = b.book_id
        WHERE sc.user_id = %s
    """, (session['user_id'],))
    
    cart_items = cursor.fetchall()
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    cursor.close()
    
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/remove_from_cart/<int:cart_id>')
def remove_from_cart(cart_id):
    if 'user_id' not in session:
        flash('Please login to modify your cart', 'danger')
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM shopping_cart WHERE cart_id = %s", (cart_id,))
    mysql.connection.commit()
    cursor.close()
    
    flash('Item removed from cart', 'success')
    return redirect(url_for('view_cart'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        flash('Please login to checkout', 'danger')
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # JOIN operation to get cart items with book details
    cursor.execute("""
        SELECT sc.quantity, b.book_id, b.title, b.price
        FROM shopping_cart sc
        JOIN books b ON sc.book_id = b.book_id
        WHERE sc.user_id = %s
    """, (session['user_id'],))
    
    cart_items = cursor.fetchall()
    
    if not cart_items:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('book_list'))
    
    total_amount = sum(item['price'] * item['quantity'] for item in cart_items)
    
    if request.method == 'POST':
        try:
            # Create order
            cursor.execute("""
                INSERT INTO orders (user_id, order_date, total_amount, status)
                VALUES (%s, %s, %s, %s)
            """, (session['user_id'], datetime.now(), total_amount, 'Processing'))
            
            order_id = cursor.lastrowid
            
            # Add order items
            for item in cart_items:
                cursor.execute("""
                    INSERT INTO order_items (order_id, book_id, quantity, price)
                    VALUES (%s, %s, %s, %s)
                """, (order_id, item['book_id'], item['quantity'], item['price']))
                
                # Update book stock
                cursor.execute("""
                    UPDATE books 
                    SET stock_quantity = stock_quantity - %s 
                    WHERE book_id = %s
                """, (item['quantity'], item['book_id']))
            
            # Clear cart
            cursor.execute("DELETE FROM shopping_cart WHERE user_id = %s", (session['user_id'],))
            
            mysql.connection.commit()
            cursor.close()
            
            flash('Order placed successfully!', 'success')
            return render_template('checkout.html', success=True)
        
        except Exception as e:
            mysql.connection.rollback()
            cursor.close()
            flash('An error occurred during checkout. Please try again.', 'danger')
            return redirect(url_for('view_cart'))
    
    cursor.close()
    return render_template('checkout.html', cart_items=cart_items, total_amount=total_amount)

# ========================
# Authentication Routes
# ========================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['user_id']
            session['name'] = user['name']
            session['is_admin'] = user.get('is_admin', False)
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        
        flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        address = request.form.get('address')
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            cursor.close()
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (name, email, password, address, is_admin)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, email, hashed_password, address, False))
        
        mysql.connection.commit()
        cursor.close()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('home'))

# ========================
# Admin Routes
# ========================

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    cursor.execute("SELECT COUNT(*) as count FROM books")
    total_books = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM orders")
    total_orders = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM users")
    total_users = cursor.fetchone()['count']
    
    cursor.execute("""
        SELECT o.order_id, o.order_date, o.total_amount, o.status, u.name as customer_name
        FROM orders o
        JOIN users u ON o.user_id = u.user_id
        ORDER BY o.order_date DESC
        LIMIT 5
    """)
    recent_orders = cursor.fetchall()
    
    cursor.close()
    
    return render_template('admin/dashboard.html', 
                         total_books=total_books,
                         total_orders=total_orders,
                         total_users=total_users,
                         recent_orders=recent_orders)

@app.route('/admin/books')
def admin_books():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM books")
    all_books = cursor.fetchall()
    cursor.close()
    
    return render_template('admin/books.html', books=all_books)

@app.route('/admin/books/add', methods=['GET', 'POST'])
def admin_add_book():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        price = float(request.form.get('price'))
        genre = request.form.get('genre')
        stock_quantity = int(request.form.get('stock_quantity'))
        description = request.form.get('description')
        
        cursor = mysql.connection.cursor()
        cursor.execute("""
            INSERT INTO books (title, author, price, genre, stock_quantity, description)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (title, author, price, genre, stock_quantity, description))
        
        mysql.connection.commit()
        cursor.close()
        
        flash('Book added successfully', 'success')
        return redirect(url_for('admin_books'))
    
    return render_template('admin/add_book.html')

@app.route('/admin/books/edit/<int:book_id>', methods=['GET', 'POST'])
def admin_edit_book(book_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        price = float(request.form.get('price'))
        genre = request.form.get('genre')
        stock_quantity = int(request.form.get('stock_quantity'))
        description = request.form.get('description')
        
        cursor.execute("""
            UPDATE books 
            SET title = %s, author = %s, price = %s, genre = %s, 
                stock_quantity = %s, description = %s
            WHERE book_id = %s
        """, (title, author, price, genre, stock_quantity, description, book_id))
        
        mysql.connection.commit()
        cursor.close()
        
        flash('Book updated successfully', 'success')
        return redirect(url_for('admin_books'))
    
    cursor.execute("SELECT * FROM books WHERE book_id = %s", (book_id,))
    book = cursor.fetchone()
    cursor.close()
    
    if not book:
        flash('Book not found', 'danger')
        return redirect(url_for('admin_books'))
    
    return render_template('admin/edit_book.html', book=book)

@app.route('/admin/books/delete/<int:book_id>')
def admin_delete_book(book_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute("DELETE FROM books WHERE book_id = %s", (book_id,))
        mysql.connection.commit()
        flash('Book deleted successfully', 'success')
    except MySQLdb.IntegrityError:
        mysql.connection.rollback()
        flash('Cannot delete book as it is referenced in orders', 'danger')
    finally:
        cursor.close()
    
    return redirect(url_for('admin_books'))

@app.route('/admin/orders')
def admin_orders():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # JOIN operation between orders and users tables
    cursor.execute("""
        SELECT o.order_id, o.order_date, o.total_amount, o.status, u.name as customer_name
        FROM orders o
        JOIN users u ON o.user_id = u.user_id
        ORDER BY o.order_date DESC
    """)
    
    all_orders = cursor.fetchall()
    cursor.close()
    
    return render_template('admin/orders.html', orders=all_orders)

@app.route('/admin/orders/<int:order_id>')
def admin_order_detail(order_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get order details with JOIN to user table
    cursor.execute("""
        SELECT o.*, u.name as customer_name, u.email, u.address
        FROM orders o
        JOIN users u ON o.user_id = u.user_id
        WHERE o.order_id = %s
    """, (order_id,))
    
    order = cursor.fetchone()
    
    if not order:
        cursor.close()
        flash('Order not found', 'danger')
        return redirect(url_for('admin_orders'))
    
    # Get order items with JOIN to books table
    cursor.execute("""
        SELECT oi.*, b.title, b.author
        FROM order_items oi
        JOIN books b ON oi.book_id = b.book_id
        WHERE oi.order_id = %s
    """, (order_id,))
    
    items = cursor.fetchall()
    cursor.close()
    
    return render_template('admin/order_detail.html', order=order, items=items)

@app.route('/admin/orders/<int:order_id>/update-status', methods=['POST'])
def admin_update_order_status(order_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    new_status = request.form.get('status')
    cursor = mysql.connection.cursor()
    cursor.execute("""
        UPDATE orders 
        SET status = %s 
        WHERE order_id = %s
    """, (new_status, order_id))
    mysql.connection.commit()
    cursor.close()
    
    flash(f'Order status updated to {new_status}', 'success')
    return redirect(url_for('admin_order_detail', order_id=order_id))

if __name__ == '__main__':
    app.run(debug=True)
