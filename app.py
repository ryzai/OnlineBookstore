from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Book, Order, OrderItem, ShoppingCart
from google_books import search_books, format_book_data
from config import Config
from datetime import datetime
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints or routes here
    register_routes(app)
    
    return app

def register_routes(app):
    @app.route('/')
    def home():
        featured_books = Book.query.order_by(Book.created_at.desc()).limit(4).all()
        return render_template('index.html', featured_books=featured_books)
    
    @app.route('/books')
    def book_list():
        search_query = request.args.get('q', '')
        
        if search_query:
            api_data = search_books(search_query)
            if api_data:
                books = format_book_data(api_data)
                return render_template('books/search_results.html', books=books, search_query=search_query)
        
        books = Book.query.all()
        return render_template('books/list.html', books=books, search_query=search_query)
    
    # Add all other routes (login, register, cart, admin, etc.)
    # ... (additional routes would go here)
    
    # CLI commands
    @app.cli.command('init-db')
    def init_db_command():
        """Initialize the database."""
        db.create_all()
        
        # Create admin user
        if not User.query.filter_by(is_admin=True).first():
            admin = User(
                name='Admin',
                email='admin@bookstore.com',
                password='admin123',
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            print('Created admin user')
        
        print('Initialized the database.')

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
