from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from models import db, User, Book, Order, OrderItem, ShoppingCart
from config import Config
from datetime import datetime
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register routes
    register_routes(app)
    
    # Context processors
    @app.context_processor
    def inject_cart_count():
        cart_count = 0
        if current_user.is_authenticated:
            cart_count = ShoppingCart.query.filter_by(user_id=current_user.id).count()
        return dict(cart_count=cart_count)
    
    return app

def register_routes(app):
    # ========================
    # Frontend Routes
    # ========================
    
    @app.route('/')
    def home():
        featured_books = Book.query.order_by(Book.created_at.desc()).limit(4).all()
        return render_template('index.html', featured_books=featured_books)
    
    @app.route('/books')
    def book_list():
        books = Book.query.all()
        return render_template('books/list.html', books=books)
    
    @app.route('/book/<int:book_id>')
    def book_detail(book_id):
        book = Book.query.get_or_404(book_id)
        return render_template('books/detail.html', book=book)
    
    @app.route('/add_to_cart', methods=['POST'])
    @login_required
    def add_to_cart():
        book_id = request.form.get('book_id')
        quantity = int(request.form.get('quantity', 1))
        
        book = Book.query.get_or_404(book_id)
        if book.stock_quantity < quantity:
            flash('Not enough stock available', 'danger')
            return redirect(url_for('book_detail', book_id=book_id))
        
        # Check if book already in cart
        cart_item = ShoppingCart.query.filter_by(
            user_id=current_user.id,
            book_id=book_id
        ).first()
        
        if cart_item:
            cart_item.quantity += quantity
        else:
            cart_item = ShoppingCart(
                user_id=current_user.id,
                book_id=book_id,
                quantity=quantity
            )
            db.session.add(cart_item)
        
        db.session.commit()
        flash('Book added to cart successfully', 'success')
        return redirect(url_for('view_cart'))
    
    @app.route('/cart')
    @login_required
    def view_cart():
        cart_items = ShoppingCart.query.filter_by(user_id=current_user.id).all()
        total = sum(item.book.price * item.quantity for item in cart_items)
        return render_template('cart/view.html', cart_items=cart_items, total=total)
    
    @app.route('/update_cart/<int:cart_id>', methods=['POST'])
    @login_required
    def update_cart(cart_id):
        cart_item = ShoppingCart.query.get_or_404(cart_id)
        quantity = int(request.form.get('quantity', 1))
        
        if quantity <= 0:
            db.session.delete(cart_item)
        else:
            cart_item.quantity = quantity
        
        db.session.commit()
        flash('Cart updated successfully', 'success')
        return redirect(url_for('view_cart'))
    
    @app.route('/remove_from_cart/<int:cart_id>')
    @login_required
    def remove_from_cart(cart_id):
        cart_item = ShoppingCart.query.get_or_404(cart_id)
        db.session.delete(cart_item)
        db.session.commit()
        flash('Item removed from cart', 'success')
        return redirect(url_for('view_cart'))
    
    @app.route('/checkout')
    @login_required
    def checkout():
        cart_items = ShoppingCart.query.filter_by(user_id=current_user.id).all()
        if not cart_items:
            flash('Your cart is empty', 'warning')
            return redirect(url_for('book_list'))
        
        total_amount = sum(item.book.price * item.quantity for item in cart_items)
        return render_template('cart/checkout.html', cart_items=cart_items, total_amount=total_amount)
    
    @app.route('/process_checkout', methods=['POST'])
    @login_required
    def process_checkout():
        cart_items = ShoppingCart.query.filter_by(user_id=current_user.id).all()
        if not cart_items:
            flash('Your cart is empty', 'warning')
            return redirect(url_for('book_list'))
        
        try:
            # Create order
            order = Order(
                user_id=current_user.id,
                total_amount=sum(item.book.price * item.quantity for item in cart_items),
                status='Processing'
            )
            db.session.add(order)
            db.session.flush()  # To get the order.id
            
            # Add order items and update stock
            for item in cart_items:
                order_item = OrderItem(
                    order_id=order.id,
                    book_id=item.book_id,
                    quantity=item.quantity,
                    price=item.book.price
                )
                db.session.add(order_item)
                
                # Update book stock
                book = Book.query.get(item.book_id)
                book.stock_quantity -= item.quantity
            
            # Clear cart
            ShoppingCart.query.filter_by(user_id=current_user.id).delete()
            
            db.session.commit()
            flash('Order placed successfully!', 'success')
            return render_template('cart/checkout_success.html', order=order)
        
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during checkout. Please try again.', 'danger')
            return redirect(url_for('checkout'))
    
    # ========================
    # Authentication Routes
    # ========================
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')
            
            user = User.query.filter_by(email=email).first()
            if user and user.verify_password(password):
                login_user(user)
                flash('Login successful!', 'success')
                next_page = request.args.get('next') or url_for('home')
                return redirect(next_page)
            
            flash('Invalid email or password', 'danger')
        return render_template('auth/login.html')
    
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            address = request.form.get('address')
            
            if User.query.filter_by(email=email).first():
                flash('Email already registered', 'danger')
                return redirect(url_for('register'))
            
            user = User(
                name=name,
                email=email,
                password=password,
                address=address,
                is_admin=False
            )
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        
        return render_template('auth/register.html')
    
    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('You have been logged out', 'info')
        return redirect(url_for('home'))
    
    # ========================
    # Admin Routes
    # ========================
    
    @app.route('/admin/dashboard')
    @login_required
    def admin_dashboard():
        if not current_user.is_admin:
            flash('Unauthorized access', 'danger')
            return redirect(url_for('home'))
        
        total_books = Book.query.count()
        total_orders = Order.query.count()
        total_users = User.query.count()
        
        recent_orders = Order.query.order_by(Order.order_date.desc()).limit(5).all()
        
        return render_template('admin/dashboard.html',
                            total_books=total_books,
                            total_orders=total_orders,
                            total_users=total_users,
                            recent_orders=recent_orders)
    
    @app.route('/admin/books')
    @login_required
    def admin_books():
        if not current_user.is_admin:
            flash('Unauthorized access', 'danger')
            return redirect(url_for('home'))
        
        books = Book.query.all()
        return render_template('admin/books.html', books=books)
    
    @app.route('/admin/books/add', methods=['GET', 'POST'])
    @login_required
    def admin_add_book():
        if not current_user.is_admin:
            flash('Unauthorized access', 'danger')
            return redirect(url_for('home'))
        
        if request.method == 'POST':
            book = Book(
                title=request.form.get('title'),
                author=request.form.get('author'),
                price=float(request.form.get('price')),
                genre=request.form.get('genre'),
                stock_quantity=int(request.form.get('stock_quantity')),
                description=request.form.get('description')
            )
            db.session.add(book)
            db.session.commit()
            flash('Book added successfully', 'success')
            return redirect(url_for('admin_books'))
        
        return render_template('admin/add_book.html')
    
    @app.route('/admin/books/edit/<int:book_id>', methods=['GET', 'POST'])
    @login_required
    def admin_edit_book(book_id):
        if not current_user.is_admin:
            flash('Unauthorized access', 'danger')
            return redirect(url_for('home'))
        
        book = Book.query.get_or_404(book_id)
        
        if request.method == 'POST':
            book.title = request.form.get('title')
            book.author = request.form.get('author')
            book.price = float(request.form.get('price'))
            book.genre = request.form.get('genre')
            book.stock_quantity = int(request.form.get('stock_quantity'))
            book.description = request.form.get('description')
            
            db.session.commit()
            flash('Book updated successfully', 'success')
            return redirect(url_for('admin_books'))
        
        return render_template('admin/edit_book.html', book=book)
    
    @app.route('/admin/books/delete/<int:book_id>')
    @login_required
    def admin_delete_book(book_id):
        if not current_user.is_admin:
            flash('Unauthorized access', 'danger')
            return redirect(url_for('home'))
        
        book = Book.query.get_or_404(book_id)
        db.session.delete(book)
        db.session.commit()
        flash('Book deleted successfully', 'success')
        return redirect(url_for('admin_books'))
    
    @app.route('/admin/orders')
    @login_required
    def admin_orders():
        if not current_user.is_admin:
            flash('Unauthorized access', 'danger')
            return redirect(url_for('home'))
        
        orders = Order.query.order_by(Order.order_date.desc()).all()
        return render_template('admin/orders.html', orders=orders)
    
    @app.route('/admin/orders/<int:order_id>')
    @login_required
    def admin_order_detail(order_id):
        if not current_user.is_admin:
            flash('Unauthorized access', 'danger')
            return redirect(url_for('home'))
        
        order = Order.query.get_or_404(order_id)
        items = OrderItem.query.filter_by(order_id=order_id).all()
        return render_template('admin/order_detail.html', order=order, items=items)
    
    @app.route('/admin/orders/<int:order_id>/update-status', methods=['POST'])
    @login_required
    def admin_update_order_status(order_id):
        if not current_user.is_admin:
            flash('Unauthorized access', 'danger')
            return redirect(url_for('home'))
        
        order = Order.query.get_or_404(order_id)
        order.status = request.form.get('status')
        db.session.commit()
        flash(f'Order status updated to {order.status}', 'success')
        return redirect(url_for('admin_order_detail', order_id=order_id))

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
