import requests
from flask import current_app

def search_books(query):
    api_key = current_app.config['GOOGLE_BOOKS_API_KEY']
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&key={api_key}&maxResults=20"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Google Books API error: {str(e)}")
        return None

def format_book_data(api_data):
    books = []
    for item in api_data.get('items', []):
        volume = item.get('volumeInfo', {})
        sale_info = item.get('saleInfo', {})
        
        books.append({
            'title': volume.get('title', 'Unknown Title'),
            'author': ', '.join(volume.get('authors', ['Unknown Author'])),
            'description': volume.get('description', 'No description available'),
            'price': sale_info.get('retailPrice', {}).get('amount', 0),
            'image': volume.get('imageLinks', {}).get('thumbnail', '/static/images/book-placeholder.png'),
            'isbn': volume.get('industryIdentifiers', [{}])[0].get('identifier', ''),
            'publisher': volume.get('publisher', 'Unknown'),
            'published_date': volume.get('publishedDate', '')
        })
    return books
