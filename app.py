import os
import re
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from yahoo_fin import stock_info as si
from yahoofinancials import YahooFinancials as yf
if os.path.exists("env.py"):
    import env


# function to check if the email is valide
# Regex solution sourced from here:
# https://www.geeksforgeeks.org/check-if-email-address-valid-or-not-in-python/
def check_email(email):
    # Check if the email iput matches the email regex.
    regex = "^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$"
    return re.search(regex, email)


# function to check if the username is valide
def check_username(name):
    # check if the username is valide
    # allow letters and hyphens. No spaces and
    # a max length of 20 character.
    regex = "^[a-zA-Z0-9]{5,20}$"
    return re.match(regex, name)


# function to check if the password is valide
def check_pw(password):
    # check if the password is valide
    # allow all characters with a max length of 5-20
    regex = "^.{5,20}$"
    return re.match(regex, password)


app = Flask(__name__)

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)


@app.route("/")
def home():
    stock_name = "uber"
    stock_price_unround = si.get_live_price(stock_name)
    stock_price = round(stock_price_unround, 2)
    # get the stock data for in the table
    stock_table = si.get_quote_table(stock_name)
    stock_info_first_part = {}
    stock_info_second_part = {}
    # make 2 dict of the data
    for index, (k, v) in enumerate(stock_table.items()):
        if index <= 8:
            add_info = {k: v}
            stock_info_first_part.update(add_info)
        else:
            add_info = {k: v}
            stock_info_second_part.update(add_info)
    return render_template(
        "index.html", stock_info_first_part=stock_info_first_part,
        stock_info_second_part=stock_info_second_part, stock_price=stock_price)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # check if the username is valide
        if request.form.get("username") == "" or not check_username(
           request.form.get("username").lower()):
            flash(
                "Username is not valide. Use between 5-15 character" +
                " and only letters and numbers.")
            return redirect(url_for("register"))
        # check if the email is valide
        if request.form.get("email") == "" or not check_email(
           request.form.get("email").lower()):
            flash("Please fill in a valid email address.")
            return redirect(url_for("register"))
        # check if the password is valide
        if request.form.get("password") == "" or not check_pw(
           request.form.get("password")):
            flash(
                "Password is not valid. use between the 5-15 " +
                "characters")
            return redirect(url_for("register"))

        # make variable to check if email address exists in db
        existing_email = mongo.db.users.find_one(
            {"email": request.form.get("email").lower()})

        # make variable to check if username address exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        # check if username already exists in db
        if existing_user:
            flash("Username already exists")
            return redirect(url_for("register"))

        # check if email already exists in db
        if existing_email:
            flash("Email already exists")
            return redirect(url_for("register"))

        # put the data from the form in a variable
        register = {
            "username": request.form.get("username").lower(),
            "email": request.form.get("email").lower(),
            "password": generate_password_hash(request.form.get("password"))
        }
        # push the data from the form to the db
        mongo.db.users.insert_one(register)

        # put the new user into 'session' cookie
        session["user"] = request.form.get("username").lower()
        flash("Registration Successful!")
        return redirect(url_for("home", username=session["user"]))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # check if the email is valide
        if request.form.get("email") == "" or not check_email(
           request.form.get("email").lower()):
            flash("Please fill in a valid email address.")
            return redirect(url_for("login"))
        # check if the password is valide
        if request.form.get("password") == "" or not check_pw(
           request.form.get("password")):
            flash(
                "Password is not valid. use between the 5-15 " +
                "characters")
            return redirect(url_for("login"))

        # make variable to check if user exists in db
        # by using the email address
        existing_user = mongo.db.users.find_one(
            {"email": request.form.get("email").lower()})

        if existing_user:
            # ensure hashed password matches user input
            if check_password_hash(
                 existing_user["password"], request.form.get("password")):
                # if the password and email do match then
                # put the usersname into session cookie
                session["user"] = existing_user[
                    "username"].lower()
                # display a welcome message to the user
                flash("Welcome, {}".format(
                    existing_user["username"].lower()))
                return redirect(url_for(
                    "home", username=session["user"]))
            else:
                # invalid password match
                flash("Incorrect Email and/or Password")
                return redirect(url_for("login"))
        else:
            # email doesn't exist
            flash("Incorrect Email and/or Password")
            return redirect(url_for("login"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    # remove user from session cookies
    flash("You have been logged out")
    session.pop("user")
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)
