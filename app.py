from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'
UPLOAD_FOLDER = './static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the uploads folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Function to get a database connection
def get_db():
    conn = sqlite3.connect('database3.db')
    conn.row_factory = sqlite3.Row
    return conn

# Initialize database
conn = get_db()
c = conn.cursor()

# Create tables
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    email TEXT UNIQUE,
    mobile TEXT,
    password TEXT
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS cart (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product TEXT,
    size TEXT,
    image TEXT,
    price REAL,
    quantity INTEGER DEFAULT 1,
    username TEXT
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product TEXT,
    size TEXT,
    image TEXT,
    price REAL,
    quantity INTEGER,
    total_price REAL,
    phone TEXT,
    address TEXT
)
''')
conn.commit()

# Landing Page
@app.route('/')
def landing():
    return render_template('landing.html')

# User Registration Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        mobile = request.form['mobile']
        password = request.form['password']

        try:
            conn = get_db()
            c = conn.cursor()
            c.execute('INSERT INTO users (username, email, mobile, password) VALUES (?, ?, ?, ?)',
                      (username, email, mobile, password))
            conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('user_login'))
        except sqlite3.IntegrityError:
            flash('Email already exists. Please try a different one.', 'danger')
    return render_template('register.html')

# User Login Route
@app.route('/user-login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password))
        user = c.fetchone()

        if user:
            session['user_logged_in'] = True
            session['user_id'] = user[0]  # Store user ID in the session
            session['username'] = user[1]
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')
    return render_template('user_login.html')

# Admin Login Route
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == 'admin' and password == '1234':
            session['admin_logged_in'] = True
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials!', 'danger')
    return render_template('admin_login.html')

# Admin Dashboard Route
@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        flash('You need to log in as admin to access the dashboard.', 'danger')
        return redirect(url_for('admin_login'))

    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM orders')
    orders = c.fetchall()
    return render_template('admin_dashboard.html', orders=orders)

# Admin Logout
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('You have been logged out as admin.', 'info')
    return redirect(url_for('admin_login'))

# User Logout
@app.route('/user/logout')
def user_logout():
    session.pop('user_logged_in', None)
    session.pop('user_id', None)
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('user_login'))

# Index Route
@app.route('/index')
def index():
    if not session.get('user_logged_in'):
        flash('You need to log in as a user to access this page.', 'danger')
        return redirect(url_for('user_login'))
    return render_template('index.html', username=session['username'])

# Cart Routes
@app.route('/product/<product_name>')
def product(product_name):
    return render_template('product.html', product_name=product_name.capitalize())

@app.route('/cart', methods=['POST'])
def cart():
    if not session.get('user_logged_in'):
        flash('You need to log in as a user to add items to the cart.', 'danger')
        return redirect(url_for('user_login'))

    product = request.form['product']
    size = request.form['size']
    image = request.files['image']
    username = session['username']  # Get the user ID from the session

    # Determine price based on size
    price = 50.0 if size == "Small" else 60.0 if size == "Medium" else 75.0

    # Save uploaded image
    image_filename = secure_filename(image.filename)
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
    image.save(image_path)

    # Add to cart with quantity 1
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO cart (product, size, image, price, quantity, username)
                 VALUES (?, ?, ?, ?, ?, ?)''', (product, size, image_filename, price, 1, username))
    conn.commit()

    flash(f"Added {product} to your cart!", 'success')
    return redirect(url_for('view_cart'))

@app.route('/cart/view')
def view_cart():
    if not session.get('user_logged_in'):
        flash('You need to log in as a user to view your cart.', 'danger')
        return redirect(url_for('user_login'))

    username = session['username']  # Get the user ID from the session
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM cart WHERE username = ?', (username,))
    cart_items = c.fetchall()

    # Calculate total price
    total_price = sum(item[4] * item[5] for item in cart_items)

    return render_template('cart.html', cart_items=cart_items, total_price=total_price)

@app.route('/cart/increase/<int:item_id>')
def increase_quantity(item_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE cart SET quantity = quantity + 1 WHERE id = ?', (item_id,))
    conn.commit()
    return redirect(url_for('view_cart'))

@app.route('/cart/decrease/<int:item_id>')
def decrease_quantity(item_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT quantity FROM cart WHERE id = ?', (item_id,))
    quantity = c.fetchone()[0]

    if quantity > 1:
        c.execute('UPDATE cart SET quantity = quantity - 1 WHERE id = ?', (item_id,))
        conn.commit()
    return redirect(url_for('view_cart'))

@app.route('/cart/remove/<int:item_id>')
def remove_item(item_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM cart WHERE id = ?', (item_id,))
    conn.commit()
    return redirect(url_for('view_cart'))

# Checkout and Order Completion
@app.route('/checkout')
def checkout():
    if not session.get('user_logged_in'):
        flash('You need to log in as a user to proceed.', 'danger')
        return redirect(url_for('user_login'))

    username = session['username']
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM cart WHERE username = ?', (username,))
    cart_items = c.fetchall()

    if not cart_items:
        return render_template('checkout.html', cart_items=None)

    # Calculate total price
    total_price = sum(item[4] * item[5] for item in cart_items)

    return render_template('checkout.html', cart_items=cart_items, total_price=total_price)

@app.route('/complete', methods=['POST'])
def complete_order():
    # Check if user is logged in
    if not session.get('user_logged_in'):
        flash('You need to log in as a user to complete the order.', 'danger')
        return redirect(url_for('user_login'))
    
    # Get form data
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    address = request.form.get('address')
    payment_method = request.form.get('payment_method')
    username = session.get('username')
    
    # Check if all required fields are provided
    if not all([first_name, last_name, email, phone, address, payment_method]):
        flash('Please fill in all required fields.', 'danger')
        return redirect(url_for('checkout'))

    # Retrieve cart items from the database
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM cart WHERE username = ?', (username,))
    cart_items = c.fetchall()
    
    # Check if cart is empty
    if not cart_items:
        flash('Your cart is empty!', 'danger')
        return redirect(url_for('checkout'))
    
    # Insert each cart item into the orders table
    total_price = 0  # Initialize total price for all items in the cart
    for item in cart_items:
        item_total = float(item[4]) * int(item[5])  # Calculate total price for each item
        total_price += item_total  # Add item total to overall total price
        
        # Insert the item into the orders table
        c.execute('''INSERT INTO orders (product, size, image, price, quantity, total_price, phone, address)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (item[1], item[2], item[3], item[4], item[5], item_total, phone, address))
    
    # Commit the order and delete cart items
    conn.commit()

    # Clear the cart
    c.execute('DELETE FROM cart WHERE username = ?', (username,))
    conn.commit()

    # Flash success message
    flash(f"Order completed successfully! Thank you, {first_name} {last_name}!", 'success')
    
    # Return the confirmation page with user details
    return render_template('complete.html', first_name=first_name, last_name=last_name, email=email,
                           phone=phone, address=address, payment_method=payment_method, total_price=total_price)

if __name__ == '__main__':
    app.run(debug=True)
