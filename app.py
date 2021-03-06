import os
import re
import math
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


# function to check if the number of stocks buy/sell is valide
def check_stock(number_stocks):
    # numbers between 1 en 10000 are allowed (not 0)
    regex = "^([1-9][0-9][0-9]{0,2}|[1-9]|10000)$"
    return re.match(regex, number_stocks)


app = Flask(__name__)

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)


# these 2 functions are made with help of:
# https://www.askpython.com/python-modules/flask/flask-error-handling
# Handling error 404 and displaying own custom page
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


# Handling error 500 and displaying own custom page
@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500


@app.route("/")
def home():
    stock_dic_info = mongo.db.stock_info.find()
    stocks = list(stock_dic_info)
    return render_template(
        "index.html", stocks=stocks, stock_dic_info=stock_dic_info)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # check if the username is valide
        request_user = request.form.get("username")
        if request_user == "" or not check_username(request_user.lower()):
            flash(
                "Username is not valide. Use between 5-15 character" +
                " and only letters and numbers.")
            return redirect(url_for("register"))
        # check if the email is valide
        request_mail = request.form.get("email")
        if request_mail == "" or not check_email(request_mail.lower()):
            flash("Please fill in a valid email address.")
            return redirect(url_for("register"))
        # check if the password is valide
        request_pw = request.form.get("password")
        if request_pw == "" or not check_pw(request_pw):
            flash(
                "Password is not valid. Use between the 5-15 " +
                "characters.")
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
            "password": generate_password_hash(request.form.get("password")),
            "cash": 10000,
            "total_spend_fees": 0
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
        request_mail = request.form.get("email")
        if request_mail == "" or not check_email(request_mail.lower()):
            flash("Please fill in a valid email address.")
            return redirect(url_for("login"))
        # check if the password is valide
        request_pw = request.form.get("password")
        if request_pw == "" or not check_pw(request_pw):
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
            if check_password_hash(existing_user["password"], request_pw):
                # if the password and email do match then
                # put the usersname into session cookie
                session["user"] = existing_user["username"].lower()
                # display a welcome message to the user
                flash("Welcome, {}".format(existing_user["username"].lower()))
                return redirect(url_for("home", username=session["user"]))
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


@app.route("/profile", methods=["GET", "POST"])
def profile():
    # get the amount of free cash of the user
    cash_of_user_unrounded = mongo.db.users.find_one(
        {"username": session["user"]})["cash"]
    cash_of_user = round(cash_of_user_unrounded, 2)
    # get the email adres of the user
    user_email = mongo.db.users.find_one(
        {"username": session["user"]})["email"]
    # get the total spend amount of cash on fees
    send_on_fees = round(mongo.db.users.find_one(
        {"username": session["user"]})["total_spend_fees"], 2)
    # get the total amount the business made by fees
    made_money = round(mongo.db.users.find_one(
        {"username": "admin"})["total_income_business"], 2)

    if request.method == "POST":
        # check if the username is valide
        request_user = request.form.get("username")
        if request_user == "" or not check_username(request_user.lower()):
            flash(
                "Username is not valide. Use between 5-15 character" +
                " and only letters and numbers.")
            return redirect(url_for("profile"))
        # check if the email is valide
        request_mail = request.form.get("email")
        if request_mail == "" or not check_email(request_mail.lower()):
            flash("Please fill in a valid email address.")
            return redirect(url_for("profile"))

        # make variable to check if email address exists in db
        existing_email = mongo.db.users.find_one(
            {"email": request.form.get("email").lower()})

        # make variable to check if username address exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        # check if username/email has been changed
        if request_user == session['user'] and request_mail == user_email:
            flash("You did not change anything.")
            return redirect(url_for("profile"))
        # check if user exists in db
        elif request_user == existing_user and request_user != session['user']:
            flash("Username already exists.")
            return redirect(url_for("profile"))
        # check if email exists in db
        elif request_mail == existing_email and request_mail != user_email:
            flash("Email in allready in use.")
            return redirect(url_for("profile"))

        # put the data from the form in a variable
        edit_profile = {
            "username": request.form.get("username").lower(),
            "email": request.form.get("email").lower(),
        }
        # push the data from the form to the db
        mongo.db.users.update_one(
            {"username": session["user"]}, {'$set': edit_profile})

        # put the new user into 'session' cookie
        session["user"] = request.form.get("username").lower()
        flash("Profile successfully edited!")
        return redirect(url_for("profile", username=session["user"]))

    return render_template(
        "profile.html", cash_of_user=cash_of_user, made_money=made_money,
        user_email=user_email, send_on_fees=send_on_fees)


@app.route("/stock/<stock_info_id>", methods=["GET", "POST"])
def stock_page(stock_info_id):
    stock_dic = mongo.db.stock_info.find_one({"_id": ObjectId(stock_info_id)})
    for key, value in stock_dic.items():
        # get the sort stock name from db
        if key == "stock_name_short":
            stock_name = value
        # get the whole stock name from db
        if key == "stock_name":
            stock_title = value
        # get the company description from db
        if key == "description":
            stock_description = value

    # get the amount of free cash of the user
    cash_of_user = mongo.db.users.find_one(
        {"username": session["user"]})["cash"]
    # variable to get the id of the stock
    get_stock_id = mongo.db.stock_info.find_one(
        {"stock_name_short": stock_name})["_id"]

    yf2 = yf(stock_name)
    # get the stock price
    stock_price = round(si.get_live_price(stock_name), 2)
    # get max amount of stocks you can buy
    max_amount = math.floor(int(cash_of_user) / stock_price)
    # the market close price of a stock
    close_price = yf2.get_prev_close_price()
    # the absoluut price change since market opening
    change_price = yf2.get_current_change()
    # the relate percent change since market opening
    change_percent_price = round(change_price*100/close_price, 2)
    # market status
    market_status = si.get_market_status()

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

    # code to buy the stocks
    if request.method == "POST":
        # define variables
        # the criteria for when the stock is allready bought by the user
        data_find = {"bought_by": session["user"],
                     "stock_name_short": stock_name}
        # the criteria to extract the price of the stock
        # of the users free cashflow
        user_of_db = {"username": session["user"]}
        # the criteria to find the user 'admin'
        user_is_admin = {"username": "admin"}

        # get the number of stocks bought
        get_stock_amount = int(request.form.get("stock_total"))
        # get the number of stocks bought in a string to valide it
        get_stock_amount_str = request.form.get("stock_total")
        # get to purchase value of the stocks excl fee
        price_change = round(stock_price * get_stock_amount, 2)
        # get amount spend on fee by purchasing a stock
        spend_on_fee = round(0.5 + (0.003 * price_change), 2)
        total_spend_stock = round(price_change + spend_on_fee, 2)

        # check if the number of stock the user wants to buy is valide
        if get_stock_amount_str == "" or not check_stock(get_stock_amount_str):
            flash("Enter a valide number.")
            return redirect(url_for("stock_page", stock_info_id=get_stock_id))

        # if user already has the stock, execute this if statement
        if mongo.db.stocks_bought.count_documents(data_find) == 1:
            # get the amount of stocks the user allready has
            stocks_user_has = mongo.db.stocks_bought.find_one(data_find)
            stocks_owned = stocks_user_has["stock_amount"]
            # get the price of the amount of stocks the user allready has
            price_user_paid = mongo.db.stocks_bought.find_one(data_find)
            stocks_price_own = price_user_paid["stock_price"]
            # get the changed price per stock
            changed_price_per_stock = (stocks_price_own + price_change)/(
                stocks_owned + get_stock_amount)

            # update the new purchase to the db
            mongo.db.stocks_bought.update_one(data_find, {'$inc': {
                "stock_price": price_change,
                "stock_amount": get_stock_amount}, '$set': {
                "price_per_stock": changed_price_per_stock}})

            # extract the stock buy price of the free cash of user and
            # add the cash spend on fee to the total spend on fees
            mongo.db.users.update_one(user_of_db, {'$inc': {
                "cash": -total_spend_stock,
                "total_spend_fees": spend_on_fee}})

            # add the fee value to the admin profile to see
            # how much the website has made so far
            mongo.db.users.update_one(user_is_admin, {'$inc': {
                "total_income_business": spend_on_fee}})

            flash(f"You successfully bought {get_stock_amount}" +
                  f" {stock_name} stocks for ${price_change}")
            return redirect(url_for("portfolio"))
        else:
            # get the price per stock
            price_per_stock = price_change / get_stock_amount

            # buy the new stock and upload the data to the db
            stock_bought = {
                "stock_name_short": stock_name,
                "stock_name": stock_title,
                "bought_by": session["user"],
                "stock_price": price_change,
                "stock_amount": get_stock_amount,
                "price_per_stock": price_per_stock
            }
            # add new stock to database
            mongo.db.stocks_bought.insert_one(stock_bought)

            # extract the stock buy price of the free cash of user and
            # add the cash spend on fee to the total spend on fees
            mongo.db.users.update_one(user_of_db, {'$inc': {
                "cash": -total_spend_stock,
                "total_spend_fees": spend_on_fee}})

            # add the fee value to the admin profile to see
            # how much the website has made so far
            mongo.db.users.update_one(user_is_admin, {'$inc': {
                "total_income_business": spend_on_fee}})

            flash(f"You successfully bought {get_stock_amount} " +
                  f"{stock_name} stocks for ${price_change}")
            return redirect(url_for("portfolio"))
        
    return render_template(
        "stock.html", stock_info_first_part=stock_info_first_part,
        stock_info_second_part=stock_info_second_part, stock_price=stock_price,
        change_percent_price=change_percent_price, stock_title=stock_title,
        max_amount=max_amount, stock_dic=stock_dic, stock_name=stock_name,
        market_status=market_status, stock_description=stock_description)


@app.route("/portfolio")
def portfolio():
    stocks_bought = list(mongo.db.stocks_bought.find())

    live_prices = {
        "GOOG": round(si.get_live_price("GOOG"), 2),
        "TSLA": round(si.get_live_price("TSLA"), 2),
        "NIO": round(si.get_live_price("NIO"), 2),
        "FSR": round(si.get_live_price("FSR"), 2),
        "AMZN": round(si.get_live_price("AMZN"), 2),
        "AAPL": round(si.get_live_price("AAPL"), 2),
        "DM": round(si.get_live_price("DM"), 2),
        "SSYS": round(si.get_live_price("SSYS"), 2),
        "DDD": round(si.get_live_price("DDD"), 2)
    }

    # get the amount of free cash of the user
    cash_of_user_unrounded = mongo.db.users.find_one(
        {"username": session["user"]})["cash"]
    cash_of_user = round(cash_of_user_unrounded, 2)
    # get the email adres of the user
    user_email = mongo.db.users.find_one(
        {"username": session["user"]})["email"]
    # get the total spend amount of cash on fees
    send_on_fees = round(mongo.db.users.find_one(
        {"username": session["user"]})["total_spend_fees"], 2)
    # get the total amount the business made by fees
    made_money = round(mongo.db.users.find_one(
        {"username": "admin"})["total_income_business"], 2)

    return render_template(
        "portfolio.html", stocks_bought=stocks_bought, made_money=made_money,
        live_prices=live_prices, cash_of_user=cash_of_user,
        user_email=user_email, send_on_fees=send_on_fees)


@app.route("/sell/<stocks_bought_id>", methods=["POST"])
def sell_stocks(stocks_bought_id):
    # find the stock the user wants to sell
    stock_dic = mongo.db.stocks_bought.find_one(
        {"_id": ObjectId(stocks_bought_id)})
    for key, value in stock_dic.items():
        # get the short stock name from db
        if key == "stock_name_short":
            stock_name = value

    # get the amount of stocks user wants to sell
    stocks_sell_amount = int(request.form.get("stocks_sell"))
    # get the number of stocks bought in a string to valide it
    stock_buy_check = request.form.get("stocks_sell")
    # get the live stock price
    stock_price_live = si.get_live_price(stock_name)
    # get the sell price of all stocks
    stock_sell_price = round(stocks_sell_amount * stock_price_live, 2)

    # check if the number of stock the user wants to buy is valide
    if stock_buy_check == "" or not check_stock(stock_buy_check):
        flash("Enter a valide number.")
        return redirect(url_for("portfolio"))

    # sell the stocks
    mongo.db.stocks_bought.update_one(stock_dic, {'$inc': {
        "stock_price": -stock_sell_price,
        "stock_amount": -stocks_sell_amount}})

    # the criteria to extract the price of the stock
    # of the users free cashflow
    user_of_db = {"username": session["user"]}
    # extract the stock buy price of the free cash of user
    mongo.db.users.update_one(user_of_db, {'$inc': {
        "cash": stock_sell_price}})

    # check if the stock file has no more stocks
    no_stocks = {"_id": ObjectId(stocks_bought_id), "stock_amount": 0}
    if mongo.db.stocks_bought.count_documents(no_stocks) == 1:
        mongo.db.stocks_bought.remove({"_id": ObjectId(stocks_bought_id)})
        flash(f"You successfully sold {stocks_sell_amount} {stock_name} " +
              f"stocks for ${stock_sell_price}")
        return redirect(url_for("portfolio"))
    else:
        flash(f"You successfully sold {stocks_sell_amount} {stock_name} " +
              f"stocks for ${stock_sell_price}")
        return redirect(url_for("portfolio"))


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=False)
