from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from forms import RegistrationForm, LoginForm
from models import db, User, Product, Order, OrderItem
from utils import ai_chat
from datetime import datetime
import os
from functools import wraps
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ----------------------------------------
# DB INIT + DEFAULT ADMIN
# ----------------------------------------
with app.app_context():
    db.create_all()
    if not User.query.filter_by(email="admin@example.com").first():
        admin = User(name="Admin", email="admin@example.com", is_admin=True)
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()



# ----------------------------------------------------
# FRONT-END WEBSITE
# ----------------------------------------------------
@app.route("/")
def index():
    q = request.args.get("q", "")
    category = request.args.get("category")
    min_price = request.args.get("min")
    max_price = request.args.get("max")

    products = Product.query

    if q:
        products = products.filter(Product.title.ilike(f"%{q}%"))

    if category:
        products = products.filter(Product.category == category)

    if min_price:
        products = products.filter(Product.price >= float(min_price))

    if max_price:
        products = products.filter(Product.price <= float(max_price))

    products = products.all()

    return render_template("index.html", products=products, q=q, category=category)


@app.route("/product/<int:pid>")
def product(pid):
    p = Product.query.get_or_404(pid)
    return render_template("product.html", product=p)



# ----------------------------------------------------
# AUTH
# ----------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(name=form.name.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for("index"))
        flash("Invalid credentials", "danger")

    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out", "info")
    return redirect(url_for("index"))



# ----------------------------------------------------
# CART + CHECKOUT
# ----------------------------------------------------
@app.route("/cart")
def view_cart():
    cart = session.get("cart", {})
    items = []
    subtotal = 0

    for pid, qty in cart.items():
        p = Product.query.get(int(pid))
        if p:
            items.append({
                "product": p,
                "qty": qty,
                "line_total": p.price * qty
            })
            subtotal += p.price * qty

    return render_template("cart.html", items=items, subtotal=subtotal)


@app.route("/cart/add/<int:pid>", methods=["POST"])
def add_to_cart(pid):
    qty = int(request.form.get("qty", 1))
    cart = session.get("cart", {})
    cart[str(pid)] = cart.get(str(pid), 0) + qty
    session["cart"] = cart
    flash("Added to cart", "success")
    return redirect(request.referrer or url_for("index"))


@app.route("/cart/remove/<int:pid>", methods=["POST"])
def remove_from_cart(pid):
    cart = session.get("cart", {})
    cart.pop(str(pid), None)
    session["cart"] = cart
    flash("Item removed", "info")
    return redirect(url_for("view_cart"))


@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cart = session.get("cart", {})
    if not cart:
        flash("Cart is empty", "warning")
        return redirect(url_for("index"))

    order = Order(user_id=current_user.id, created_at=datetime.utcnow(), status="Processing")
    db.session.add(order)

    subtotal = 0
    for pid, qty in cart.items():
        p = Product.query.get(int(pid))
        if p:
            item = OrderItem(order=order, product_id=p.id, price=p.price, quantity=qty)
            db.session.add(item)
            subtotal += p.price * qty

    order.total = subtotal
    db.session.commit()
    session.pop("cart", None)

    flash("Order placed successfully!", "success")
    return redirect(url_for("order_history"))


@app.route("/orders")
@login_required
def order_history():
    orders = Order.query.filter_by(user_id=current_user.id).all()
    return render_template("order_history.html", orders=orders)



# ----------------------------------------------------
# ADMIN SYSTEM
# ----------------------------------------------------

# decorator for admin authentication
def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Admin access only!", "danger")
            return redirect(url_for("admin_login"))
        return func(*args, **kwargs)
    return wrapper



# -----------------------------
# ADMIN LOGIN
# -----------------------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password) and user.is_admin:
            login_user(user)
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid admin credentials", "danger")

    return render_template("admin_login.html")



# -----------------------------
# BASIC ADMIN DASHBOARD
# -----------------------------
@app.route("/admin/dashboard")
@login_required
@admin_required
def admin_dashboard():
    total_products = Product.query.count()
    total_users = User.query.count()
    total_orders = Order.query.count()

    return render_template(
        "admin_dashboard.html",
        total_products=total_products,
        total_users=total_users,
        total_orders=total_orders
    )



# -----------------------------
# ADVANCED ADMIN DASHBOARD
# -----------------------------
@app.route("/admin/dashboard/advanced")
@login_required
@admin_required
def admin_dashboard_advanced():
    total_sales = sum(o.total for o in Order.query.all())

    stats = {
        "products": Product.query.count(),
        "users": User.query.count(),
        "orders": Order.query.count(),
        "total_sales": total_sales
    }

    return render_template("admin_dashboard_advanced.html", stats=stats)



# -----------------------------
# ADMIN — ALL USERS
# -----------------------------
@app.route("/admin/users")
@login_required
@admin_required
def admin_users():
    users = User.query.all()
    return render_template("admin_users.html", users=users)



# -----------------------------
# ADMIN — ALL ORDERS
# -----------------------------
@app.route("/admin/orders")
@login_required
@admin_required
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("admin_orders.html", orders=orders)



# -----------------------------
# ADMIN — PRODUCTS LIST
# -----------------------------
@app.route("/admin/products")
@login_required
@admin_required
def admin_products():
    products = Product.query.all()
    return render_template("admin_products.html", products=products)



# -----------------------------
# ADMIN — ADD PRODUCT (FINAL)
# -----------------------------
@app.route("/admin/products/add", methods=["GET", "POST"])
@login_required
@admin_required
def admin_add_product():
    if request.method == "POST":
        title = request.form.get("title")
        price = float(request.form.get("price") or 0)
        description = request.form.get("description")
        category = request.form.get("category")

        # File upload
        image = request.files.get("image")
        image_path = None

        if image and image.filename:
            upload_dir = "static/uploads"
            os.makedirs(upload_dir, exist_ok=True)
            image_path = f"{upload_dir}/{image.filename}"
            image.save(image_path)

        p = Product(
            title=title,
            price=price,
            description=description,
            category=category,
            image=image_path
        )

        db.session.add(p)
        db.session.commit()

        flash("Product added!", "success")
        return redirect(url_for("admin_products"))

    return render_template("admin_add_product.html")



# -----------------------------
# ADMIN — EDIT PRODUCT
# -----------------------------
@app.route("/admin/products/edit/<int:pid>", methods=["GET", "POST"])
@login_required
@admin_required
def admin_edit_product(pid):
    product = Product.query.get_or_404(pid)

    if request.method == "POST":
        product.title = request.form.get("title")
        product.price = float(request.form.get("price"))
        product.description = request.form.get("description")
        product.category = request.form.get("category")

        image = request.files.get("image")
        if image and image.filename:
            upload_dir = "static/uploads"
            os.makedirs(upload_dir, exist_ok=True)
            image_path = f"{upload_dir}/{image.filename}"
            image.save(image_path)
            product.image = image_path

        db.session.commit()
        flash("Product updated!", "success")
        return redirect(url_for("admin_products"))

    return render_template("admin_edit_product.html", product=product)



# -----------------------------
# ADMIN — DELETE PRODUCT
# -----------------------------
@app.route("/admin/products/delete/<int:pid>", methods=["POST"])
@login_required
@admin_required
def admin_delete_product(pid):
    p = Product.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    flash("Product removed", "info")
    return redirect(url_for("admin_products"))



# ----------------------------------------------------
# AI CHATBOT API
# ----------------------------------------------------
@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.json or {}
    prompt = data.get("prompt", "")

    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    resp = ai_chat(prompt)
    return jsonify({"reply": resp})



# ----------------------------------------------------
# RUN APP
# ----------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
