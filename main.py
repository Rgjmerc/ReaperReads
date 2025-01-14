from flask import Flask, render_template, request, redirect, flash, abort
import flask_login
import pymysql
from dynaconf import Dynaconf

app = Flask(__name__)

conf = Dynaconf(
    settings_file = ["settings.toml"]
)

app.secret_key = conf.secret_key

login_manager = flask_login.LoginManager()
login_manager.init_app(app)
login_manager.login_view = "/signin"

class User:
    is_authenticated = True
    is_anonymous = False
    is_active = True
    def __init__(self, user_id, username, email, first_name, last_name):
        self.id = user_id
        self.username = username
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
    def get_id(self):
        return str(self.id)

@login_manager.user_loader

def load_user(user_id):
    conn = connectdb()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM `Customer` WHERE `id` = {user_id};")
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    if result is not None:
        return User(result["id"], result["username"], result["email"], result["first_name"], result["last_name"])

def connectdb():
    conn = pymysql.connect(
        host = "10.100.34.80",
        database = "lvergara_reaper_reads",
        user = "lvergara",
        password = conf.password,
        autocommit = True,
        cursorclass = pymysql.cursors.DictCursor
    )
    return conn

@app.route("/")
def index ():
    return render_template("homepage.html.jinja")

@app.route("/browse")
def product_browse():
    query = request.args.get("query")
    conn = connectdb()
    cursor = conn.cursor()
    if query is None:
        cursor.execute("SELECT * FROM `Product`;")
    else:
        cursor.execute(f"SELECT * FROM `Product` WHERE `name` LIKE '%{query}%' OR `description` LIKE '%{query}%';")
    results = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("browse.html.jinja", products = results, query = query)

@app.route("/product/<product_id>")
def product_page(product_id):
    conn = connectdb()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM `Product` WHERE `id` = {product_id};")
    result = cursor.fetchone()
    if result is None:
        abort(404)
    cursor.execute(f""" SELECT
    `customer_id`,`product_id`,`content`,`rating`,
    `Reviews`.`timestamp`,`username`
    FROM `Reviews`
    JOIN `Customer` ON `customer_id` = `Customer`.`id`
    WHERE `product_id` = {product_id};
    """)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("product.html.jinja",product = result, reviews = results)

@app.route("/product/<product_id>/cart", methods = ["POST"])
@flask_login.login_required
def add_cart(product_id):
    quantity = request.form["qty"]
    customer_id = flask_login.current_user.id
    conn = connectdb()
    cursor = conn.cursor()
    cursor.execute(f"""
    INSERT INTO `Cart`
        (`quantity`, `customer_id`, `product_id`)
    VALUE
        ('{quantity}','{customer_id}','{product_id}')
    ON DUPLICATE KEY UPDATE
        `quantity` = `quantity` + {quantity}
    """)
    cursor.close()
    conn.close()
    return redirect ("/cart")


@app.route("/signup", methods = ["POST", "GET"])
def signup():
    if flask_login.current_user.is_authenticated:
        return redirect ("/")
    else:
        if request.method == "POST":
            first_name = request.form["fname"]
            last_name = request.form["lname"]
            username = request.form["username"]
            password = request.form["pass"]
            confirmpassword = request.form["confirmpass"]
            email = request.form["email"]
            address = request.form["address"]
            conn = connectdb()
            cursor = conn.cursor()
            if len(password) < 8:
                flash("Password contains less than 8 characters")
            if confirmpassword != password:
                flash("The passwords don't match")
            else:
                try:
                    cursor.execute(f"""
                    INSERT INTO `Customer` 
                        (`first_name`, `last_name`, `username`, `password`, `email`, `address`)
                    VALUE
                        ('{first_name}', '{last_name}', '{username}', '{password}', '{email}', '{address}');
                    """)
                except pymysql.err.IntegrityError:
                    flash("Username/Email is already in use")
                else:    
                    return redirect("/signin") 
                finally:
                    cursor.close()
                    conn.close()

        return render_template("signup.html.jinja")
    
@app.route("/signin", methods = ["POST","GET"])
def signin():
    if flask_login.current_user.is_authenticated:
        return redirect ("/")
    else:
        if request.method == "POST":
            username = request.form["username"].strip()
            password = request.form["pass"]
            conn = connectdb()
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM `Customer` WHERE `username` = '{username}' OR `email` = '{username}';")
            result = cursor.fetchone()
            if result is None:
                flash("Your Username/Password is incorrect")
            elif password != result["password"]:
                flash("Your Username/Password is incorrect")
            else:
                user = User(result["id"], result["username"], result["email"], result["first_name"], result["last_name"])
                flask_login.login_user(user)
                cursor.close()
                conn.close()
                return redirect("/browse")
        cursor.close()
        conn.close()    
        return render_template("signin.html.jinja")

@app.route("/logout")
def logout():
    flask_login.logout_user()
    return redirect("/")

@app.route("/cart")
@flask_login.login_required
def cart():
    conn = connectdb()
    cursor = conn.cursor()
    customer_id = flask_login.current_user.id
    cursor.execute(f"""SELECT `name`,`price`,`quantity`,`image`,`product_id`,`Cart`.`id` 
    FROM `Cart` JOIN `Product` ON `product_id` = `Product`.`id`
    WHERE `customer_id` = {customer_id};""")
    result = cursor.fetchall()
    total = 0
    for product in result:
        quantity = product["quantity"]
        price = product["price"]
        item_total = price * quantity
        total = item_total + total
    cursor.close()
    conn.close()
    return render_template("cart.html.jinja", products = result, total = total)

@app.route("/cart/<cart_id>/del", methods = ["POST"])
@flask_login.login_required
def delete(cart_id):
    conn = connectdb()
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM `Cart` WHERE `id`={cart_id};")
    cursor.close()
    conn.close()
    return redirect("/cart")

@app.route("/cart/<cart_id>/upd", methods = ["POST"])
@flask_login.login_required
def upd(cart_id):
    conn = connectdb()
    cursor = conn.cursor()
    qty = request.form["qty"]
    cursor.execute(f"UPDATE `Cart` SET `quantity`={qty} WHERE `id`={cart_id};")
    cursor.close()
    conn.close()
    return redirect("/cart")

@app.route("/checkout")
@flask_login.login_required
def checkout():
    customer_id = flask_login.current_user.id
    conn = connectdb()
    cursor = conn.cursor()
    cursor.execute(f"""SELECT `name`,`price`,`quantity`,`image`,`product_id`,`Cart`.`id` 
    FROM `Cart` JOIN `Product` ON `product_id` = `Product`.`id`
    WHERE `customer_id` = {customer_id};""")
    result = cursor.fetchall()
    total = 0
    tax = 0.08875
    for product in result:
        quantity = product["quantity"]
        price = product["price"]
        item_total = price * quantity
        total = item_total + total

    tax_total = total * tax
    overall_total = total + tax_total

    cursor.close()
    conn.close()
    return render_template("checkout.html.jinja", products = result, total = total, overall_total = overall_total, tax_total = tax_total)

@app.route("/sale")
@flask_login.login_required
def sale():
    conn = connectdb()
    cursor = conn.cursor()
    customer_id = flask_login.current_user.id
    cursor.execute(f"INSERT INTO `Sale`  (`customer_id`) VALUES ({customer_id});")
    sale_id = cursor.lastrowid()
    cursor.execute(f"SELECT `product_id`,`quantity` FROM `Cart`;")
    result = cursor.fetchall()
    for product in result:
        quantity = product["quantity"]
        product_id = product["product_id"]
        cursor.execute(f"INSERT INTO `SaleProduct` (`sale_id`,`product_id`,`quantity`) VALUES ({sale_id},{product_id},{quantity});")
    saleproduct = cursor.fetchall()
    cursor.execute(f"DELETE FROM `Cart` WHERE `customer_id` = {customer_id};")
    cursor.close()
    conn.close()
    return redirect("/thanks", saleproduct = saleproduct)

@app.route("/product/<product_id>/review", methods = ["POST"])
def review(product_id):
    conn = connectdb()
    cursor = conn.cursor()
    customer_id = flask_login.current_user.id
    content = request.form["content"]
    rate = request.form["rate"]
    cursor.execute(f"""
    INSERT INTO `Reviews`
    (`customer_id`,`product_id`,`content`,`rating`)
    VALUE
    ('{customer_id}','{product_id}','{content}','{rate}')
    ;""")
    cursor.close()
    conn.close()
    return redirect(f"/product/{product_id}")