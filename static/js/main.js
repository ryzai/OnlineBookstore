// Cart count update
document.addEventListener('DOMContentLoaded', function() {
    // Update cart count in navbar
    function updateCartCount() {
        fetch('/api/cart/count')
            .then(response => response.json())
            .then(data => {
                document.getElementById('cart-count').textContent = data.count;
            });
    }
    
    // Call initially and set interval to update periodically
    updateCartCount();
    setInterval(updateCartCount, 30000); // Update every 30 seconds
    
    // Add to cart buttons
    document.querySelectorAll('.add-to-cart').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const bookId = this.dataset.bookId;
            
            fetch('/cart/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ book_id: bookId, quantity: 1 })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateCartCount();
                    alert('Book added to cart!');
                } else {
                    alert(data.message || 'Error adding to cart');
                }
            });
        });
    });
    
    // Quantity input validation
    document.querySelectorAll('input[type="number"]').forEach(input => {
        input.addEventListener('change', function() {
            const max = parseInt(this.max);
            const min = parseInt(this.min);
            let value = parseInt(this.value);
            
            if (isNaN(value)) value = min;
            if (value > max) value = max;
            if (value < min) value = min;
            
            this.value = value;
        });
    });
});