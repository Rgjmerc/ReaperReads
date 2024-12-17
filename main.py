from flask import Flask, render_template, request, redirect, flash
import pymysql
from dynaconf import Dynaconf

app = Flask(__name__)

conf = Dynaconf(
    settings_file = ["settings.toml"]
)

app.secret_key = conf.secret_key

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
    cursor.close()
    conn.close()
    return render_template("product.html.jinja",product = result)
@app.route("/signup", methods = ["POST", "GET"])
def signup():
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
    
@app.route("/signin")
def signin():
    return render_template("signin.html.jinja")