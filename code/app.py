from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
UPLOAD_FOLDER = './static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the uploads folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Initialize database
conn = sqlite3.connect('database.db', check_same_thread=False)
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS cart (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product TEXT,
    size TEXT,
    image TEXT,
    price REAL,
    quantity INTEGER DEFAULT 1
)
''')
conn.commit()


# Helper function to get cart item count
def get_cart_count():
    c.execute('SELECT SUM(quantity) FROM cart')
    result = c.fetchone()[0]
    return result if result else 0


# Make cart count available globally
@app.context_processor
def inject_cart_count():
    return {'cart_count': get_cart_count()}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/product/<product_name>')
def product(product_name):
    return render_template('product.html', product_name=product_name.capitalize())


@app.route('/cart', methods=['POST'])
def cart():
    product = request.form['product']
    size = request.form['size']
    image = request.files['image']

    # Determine price based on size
    price = 50.0 if size == "Small" else 60.0 if size == "Medium" else 75.0

    # Save uploaded image
    image_filename = image.filename
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
    image.save(image_path)

    # Add to cart with quantity 1
    c.execute('''
        INSERT INTO cart (product, size, image, price, quantity)
        VALUES (?, ?, ?, ?, ?)
    ''', (product, size, image_filename, price, 1))
    conn.commit()

    return redirect(url_for('view_cart'))


@app.route('/cart/view')
def view_cart():
    c.execute('SELECT * FROM cart')
    cart_items = c.fetchall()

    # Calculate total price
    total_price = sum(item[4] * item[5] for item in cart_items)

    return render_template('cart.html', cart_items=cart_items, total_price=total_price)


@app.route('/cart/increase/<int:item_id>')
def increase_quantity(item_id):
    c.execute('UPDATE cart SET quantity = quantity + 1 WHERE id = ?', (item_id,))
    conn.commit()
    return redirect(url_for('view_cart'))


@app.route('/cart/decrease/<int:item_id>')
def decrease_quantity(item_id):
    c.execute('SELECT quantity FROM cart WHERE id = ?', (item_id,))
    quantity = c.fetchone()[0]

    if quantity > 1:
        c.execute('UPDATE cart SET quantity = quantity - 1 WHERE id = ?', (item_id,))
        conn.commit()
    return redirect(url_for('view_cart'))


@app.route('/cart/remove/<int:item_id>')
def remove_item(item_id):
    c.execute('DELETE FROM cart WHERE id = ?', (item_id,))
    conn.commit()
    return redirect(url_for('view_cart'))


@app.route('/checkout')
def checkout():
    c.execute('SELECT * FROM cart')
    cart_items = c.fetchall()

    # Calculate total price
    total_price = sum(item[4] * item[5] for item in cart_items)

    return render_template('checkout.html', cart_items=cart_items, total_price=total_price)


@app.route('/complete', methods=['POST'])
def complete_order():
    phone = request.form['phone']
    address = request.form['address']

    # Clear cart after completing the order
    c.execute('DELETE FROM cart')
    conn.commit()

    return f'''
        <h1>Order Completed!</h1>
        <p>Thank you for your purchase. Your order will be delivered to:</p>
        <p><strong>Phone:</strong> {phone}</p>
        <p><strong>Address:</strong> {address}</p>
        <a href="/" class="btn btn-primary">Go Home</a>
    '''


if __name__ == '__main__':
    app.run(debug=True)
