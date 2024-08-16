import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import json
import hashlib
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'
UPLOAD_FOLDER = 'static/images/products'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Load users from JSON file
def load_users():
    with open('users.json') as file:
        return json.load(file)['users']

users = load_users()

# Load products from JSON file
def load_products():
    with open('products.json', 'r') as file:
        return json.load(file)

def save_products(products):
    with open('products.json', 'w') as file:
        json.dump(products, file, indent=4)

products = load_products()

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = hashlib.md5(password.encode()).hexdigest()
        
        for user in users:
            if user['username'] == username and user['password'] == hashed_password:
                session['username'] = username
                return redirect(url_for('dashboard'))
        return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        hashed_password = hashlib.md5(password.encode()).hexdigest()
        
        new_user = {
            'username': username,
            'password': hashed_password,
            'email': email
        }
        
        users.append(new_user)
        
        with open('users.json', 'w') as file:
            json.dump({'users': users}, file, indent=4)
        
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        # Add your reset password logic here
        return redirect(url_for('login'))
    return render_template('reset_password.html')

@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        username = session['username']
        return render_template('dashboard.html', username=username)
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/mens')
def mens():
    products = load_products()
    mens_products = {k: v for k, v in products.items() if v['section'] == 'mens'}
    return render_template('mens.html', products=mens_products)

@app.route('/womens')
def womens():
    products = load_products()
    womens_products = {k: v for k, v in products.items() if v['section'] == 'womens'}
    return render_template('womens.html', products=womens_products)

@app.route('/more')
def more():
    products = load_products()
    more_products = {k: v for k, v in products.items() if v['section'] == 'more'}
    return render_template('more.html', products=more_products)


@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    product_key = str(product_id)

    if 'cart' not in session:
        session['cart'] = {}
    
    if product_key in session['cart']:
        session['cart'][product_key] += 1
    else:
        session['cart'][product_key] = 1
    
    flash('Product added to cart successfully!', 'success')
    return redirect(url_for('show_cart'))
    

@app.route('/show_cart')
def show_cart():
    cart = session.get('cart', {})
    product_details = {}

    for pid, qty in cart.items():
        if pid in products:
            product_details[pid] = {
                'name': products[pid]['name'],
                'quantity': qty,
                'price': products[pid]['price'],
                'image_url': products[pid]['image_url']
            }

    return render_template('cart.html', cart=product_details)

@app.route('/update_quantity/<int:product_id>', methods=['POST'])
def update_quantity(product_id):
    product_key = str(product_id)
    new_quantity = int(request.form.get('quantity'))
    
    if 'cart' in session and product_key in session['cart']:
        session['cart'][product_key] = new_quantity
        flash('Product quantity updated!', 'success')
    return redirect(url_for('show_cart'))

@app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    product_key = str(product_id)
    
    if 'cart' in session and product_key in session['cart']:
        session['cart'].pop(product_key)
        flash('Product removed from cart!', 'success')
    return redirect(url_for('show_cart'))

@app.route('/settings')
def settings():
    if 'username' in session:
        return render_template('settings.html')
    return redirect(url_for('login'))

@app.route('/payment')
def payment():
    cart = session.get('cart', {})
    total_amount = sum(products[pid]['price'] * qty for pid, qty in cart.items())
    return render_template('payment.html', total_amount=total_amount)

@app.route('/process_payment', methods=['POST'])
def process_payment():
    # Implement payment processing logic here (e.g., integrate with a payment gateway)
    # For this example, we will just clear the cart and show a success message
    flash('Payment processed successfully!', 'success')
    session.pop('cart', None)  # Clear the cart after payment
    return redirect(url_for('dashboard'))

# Product management routes
@app.route('/manage_product', methods=['POST'])
def manage_product():
    data = request.get_json()
    product_id = data['product_id']
    action = data['action']

    if action == 'delete':
        products.pop(product_id, None)
        save_products(products)
        return jsonify({'status': 'success', 'message': 'Product deleted successfully'})

    return jsonify({'status': 'error', 'message': 'Invalid action'})

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        product_name = request.form['product_name']
        description = request.form['description']
        price = float(request.form['price'])
        section = request.form['section']

        if 'image' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        
        file = request.files['image']
        
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = url_for('static', filename='images/products/' + filename)

            new_product_id = str(max(map(int, products.keys())) + 1)
            products[new_product_id] = {
                'name': product_name,
                'description': description,
                'price': price,
                'image_url': image_url,
                'section': section
            }
            
            save_products(products)
            flash('Product added successfully!', 'success')
            return redirect(url_for('add_product'))
        else:
            flash('File type not allowed', 'error')
            return redirect(request.url)
    return render_template('add_product.html')


if __name__ == '__main__':
    app.run(debug=True)
