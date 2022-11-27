# CS50 - Final Project
import os
from flask import Flask, flash, render_template
# Login Required Decorator
from flask import redirect, render_template, request, session
from functools import wraps
# Password
from werkzeug.security import check_password_hash, generate_password_hash
from flask_session import Session
# Call API
import requests
import urllib.parse
import json
# Scheduled tasks
from apscheduler.schedulers.background import BackgroundScheduler
import time
from flask_mail import Mail, Message
# from flask_sqlalchemy import SQLAlchemy
# from flask_marshmallow import Marshmallow
import sqlite3
from cs50 import SQL
from collections import defaultdict # Dictionary
from datetime import datetime


# instantiate flask app
app = Flask(__name__)

@app.route("/trial")
def trial():
    return render_template('trial.html')

# ------------------------------------------------------------------
def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# ------------------------------------------------------------------
# Database
db = SQL("sqlite:///database.db")

# ------------------------------------------------------------------
# global variables
symbolSum = []
stockValue = []
currentValue = []
stockProfit = []

# ------------------------------------------------------------------
# configuration of mail
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'billsfoodpmsalert@gmail.com'
app.config['MAIL_PASSWORD'] = 'rnplygpaxuxahgnd'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

# instantiate the mail class
mail = Mail(app)

# ------------------------------------------------------------------
@app.route("/")
@login_required
def home():    
    return render_template('home.html')


@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():  
    # Query database for stock
    stockList = db.execute("SELECT symbol FROM transactions WHERE user_id=:user_id GROUP BY symbol", user_id=session["user_id"])
    
    symbol = []
    name = []
    price = []
    date = []
    time = []
    
    # Get real time information by calling API
    for stock in stockList:
        symbol.append(stock['symbol'])
        getName = getData(stock['symbol'])['name']
        name.append(getName)
        getPrice = getData(stock['symbol'])['price']
        price.append(getPrice)
        getTime = getData(stock['symbol'])['time']
        realTime = datetime.fromtimestamp(getTime/1000).strftime("%H:%M:%S") # %d-%m-%Y, %H:%M:%S
        time.append(realTime)
        getDate = datetime.fromtimestamp(getTime/1000).strftime("%Y-%m-%d")
        date.append(getDate)
           
    APIdata = [symbol, name, price, date, time]
    
    # Stock summary
    stock_record = db.execute("SELECT symbol, SUM(shares), SUM(transact_amount), action FROM transactions WHERE user_id=:user_id GROUP BY symbol, action", user_id=session["user_id"])
    
    # Find shares owned
    shares_buy = 0
    shares_sell = 0
    amount_buy = 0
    amount_sell = 0
    sharesSum = []
    
    for stock in stock_record:
        for symbol in stockList:
            if stock['symbol'] == symbol['symbol']:
                if stock['action'] == 'BUY':
                    shares_buy = stock['SUM(shares)']
                    amount_buy = stock['SUM(transact_amount)']
                else:
                    shares_sell = stock['SUM(shares)']
                    amount_sell = stock['SUM(transact_amount)']
                
                shares_owned = round(shares_buy - shares_sell, 2)
                sharesSum.append(shares_owned)
                symbolSum.append(stock['symbol'])
                
                amount_owned = round(amount_buy - amount_sell, 2)
                stockValue.append(amount_owned)
                
                currentPrice = round(getData(stock['symbol'])['price'], 2)
                currentValue.append(shares_owned * currentPrice)
                
                profit = round((currentPrice - amount_owned) / amount_owned * 100, 2)
                stockProfit.append(profit)
    
    stockValue_neg = [-1* i for i in stockValue]
           
    stockSum = [symbolSum, sharesSum, stockValue, currentValue, stockProfit, stockValue_neg]
    

    return render_template('dashboard.html', APIdata=APIdata, stockSum=stockSum)


def getData(symbol):
    base_url = 'https://sandbox.iexapis.com/'
    version = 'stable/'

    # Add your publishable API token here.
    token = 'Tsk_2a0172aa307b4cba8a50964ec127396c'

    # First example: get one monthof Historical Daily prices for international symbols.
    symbol_param = symbol
    endpoint_path = f'stock/{symbol_param}/quote'
    query_params = f'?token={token}'
    api_call = f'{base_url}{version}{endpoint_path}{query_params}'
    print(f'API Call: {api_call}') # The resulting API call should be: https://sandbox.iexapis.com/stable/stock/T/quote?token=YOUR_TOKEN

    # Contact API
    try:
        response = requests.get(api_call) # Make HTTPS call
        response.raise_for_status()
    except response.RequestException:
        return None
        
    # Parse response
    try:
        data = response.json() # Decode JSON
        return {
            "name": data["companyName"],
            "price": float(data["latestPrice"]),
            "symbol": data["symbol"],
            "date": data["latestTime"],
            "time": data["latestUpdate"]
        }
        

    except (KeyError, TypeError, ValueError):
        return None
    

# Sell Notification
def ScheduledRequest():
    
    for i in range(len(stockProfit)):
        # Notification to sell stock if profit > 10%
        if (stockProfit >= 10):
            with app.app_context():
                msg = Message(
                            'Notification to sell the stock',
                            sender ='smtp.gmail.com',
                            recipients = ['xxxxxxxxxx@gmail.com']
                            )
                msg.body = f'Stock Symbol: {symbolSum[i]} \n Current Price: {currentValue[i]} \n Profit: {stockProfit[i]}%'
                mail.send(msg)

        # Notification to sell stock if profit < 10%
        if (stockProfit <= -10):
            with app.app_context():
                msg = Message(
                            'Notification to sell the stock',
                            sender ='smtp.gmail.com',
                            recipients = ['xxxxxxxxxx@gmail.com']
                            )
                msg.body = f'Stock Symbol: {symbolSum[i]} \n Current Price: {currentValue[i]} \n Profit: {stockProfit[i]}%'
                mail.send(msg)

# Check the price every 5 mins
sched = BackgroundScheduler(daemon=True)
sched.add_job(ScheduledRequest,'interval',minutes=5)
sched.start()


# ------------------------------------------------------------------
# Transaction record
@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    stock_data = db.execute("SELECT * FROM transactions WHERE user_id=:user_id", user_id=session["user_id"])
    
    # # Store into list
    histDate = []
    histTime = []
    histSymbol = []
    histName = []
    action = []
    shares = []
    histPrice = []
    amount = []
    
    for stock in stock_data:
        histDate.append(stock["date"])
        timeframe = datetime.fromtimestamp(stock["time"]/10000).strftime("%H:%M:%S") # %d-%m-%Y, %H:%M:%S
        histTime.append(timeframe)
        histSymbol.append(stock["symbol"])
        # stock_name = getData(stock["symbol"])["name"]
        histName.append(stock["company"])
        action.append(stock["action"])
        shares.append(stock["shares"])
        histPrice.append(stock["price"])
        amount.append(stock["transact_amount"])
    
    histData = [histDate, histTime, histSymbol, histName, action, shares, histPrice, amount]
    
    return render_template("history.html", histData=histData)


# ------------------------------------------------------------------
# Transaction
@app.route("/transaction")
@login_required
def transaction():
    return render_template("transaction.html")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    
    # The form is submitted via POST
    if request.method == "POST":
        
        symbol = request.form.get("symbol").upper()
        shares = request.form.get("shares")
        
        getQuote = getData(symbol)
        
        # Lookup the stock symbol and check no. of shares
        if not symbol:
            return apology("Please provide a symbol", 400)
            
        elif not getQuote:
            return apology("Please input correct symbol", 400)
        
        if not shares:
            return apology("Please provide no. of shares", 400)
        
        elif not shares.isdigit():
            return apology("Please input a positive integer for shares", 400)

        else:
            company = getQuote['name']
            date = getQuote["date"]
            time = getQuote["time"]
            price = float(getQuote["price"])
            transact_amount = int(shares) * float(price)
            action = "BUY"
            
            # # Check if cash is enough for transaction
            # cash = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])
            # cash = cash[0]["cash"]
            
            # cash_remain =  float(cash) - transact_amount
            # if cash_remain < 0:
            #     return apology("Not enough cash", 403)
            
            # Display the results
            # else:
                # Add new table to database using appropriate SQL types
                # db.execute("UPDATE users SET cash=:cash WHERE id=:id", cash=cash_remain, id=session["user_id"])
            buy = db.execute("INSERT INTO transactions (user_id, symbol, company, shares, price, action, transact_amount, date, time) VALUES (:user_id, :symbol, :company, :shares, :price, :action, :transact_amount, :date, :time)",
                                    user_id=session["user_id"], 
                                    symbol=symbol,
                                    company=company,
                                    shares=shares, 
                                    price=price, 
                                    action=action,
                                    transact_amount=transact_amount,
                                    date=date,
                                    time=time)
            
            return render_template("home.html")
    
    return render_template("buy.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
       
    # The form is submitted via POST
    if request.method == "POST":
        
        symbol = request.form.get("symbol").upper()
        shares = request.form.get("shares")
        
        getQuote = getData(symbol)
        
        # # Lookup the stock symbol and check no. of shares
        # if not symbol:
        #     return apology("Please provide a symbol", 400)
            
        # if not getQuote:
        #     return apology("Please input correct symbol", 400)
        
        # if not shares:
        #     return apology("Please provide no. of shares", 400)
        
        # if shares.isdigit() == False:
        #     return apology("Please input a positive integer for shares", 400)
        
        
        # Check stock exist in transaction record and have enough stock to sell
        stock_record = db.execute("SELECT symbol, SUM(shares), action FROM transactions WHERE user_id=:user_id GROUP BY symbol, action", user_id=session["user_id"])
        
        # Find shares owned
        shares_buy = 0
        shares_sell = 0
        
        for stock in stock_record:
            if stock['symbol'] == symbol:
                if stock['action'] == 'BUY':
                    shares_buy = stock['SUM(shares)']
                else:
                    shares_sell = stock['SUM(shares)']
                    
        shares_owned = shares_buy - shares_sell
        print(shares_owned)
        
        # if int(shares) > int(shares_owned):
        #         return apology("Not enough shares to sell", 400)
        #         print("Not enough shares to sell")
        
        # else:
        company = getQuote['name']
        date = getQuote["date"]
        time = getQuote["time"]
        price = float(getQuote["price"])
        transact_amount = int(shares) * float(price)
        action = "SELL"
            
            # # Check if cash is enough for transaction
            # cash = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])
            # cash = cash[0]["cash"]
            
            # cash =  float(cash) + transact_amount

            # Add new table to database using appropriate SQL types
            # db.execute("UPDATE users SET cash=:cash WHERE id=:id", cash=cash, id=session["user_id"])
        sell = db.execute("INSERT INTO transactions (user_id, symbol, company, shares, price, action, transact_amount, date, time) VALUES (:user_id, :symbol, :company, :shares, :price, :action, :transact_amount, :date, :time)",
                                user_id=session["user_id"], 
                                symbol=symbol,
                                company=company,
                                shares=shares, 
                                price=price, 
                                action=action,
                                transact_amount=transact_amount,
                                date=date,
                                time=time)
        
        return render_template("home.html")

    else:
        # Get stocks symbol
        stocks = db.execute("SELECT symbol FROM transactions WHERE user_id=:user_id GROUP BY symbol", user_id=session["user_id"])
        
        stocks_opt = []
        for i in stocks:
            stocks_opt.append(i["symbol"])
        
        return render_template("sell.html", stocks_opt=stocks_opt)
    
    
# ------------------------------------------------------------------
@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    
    if request.method == "POST":
        symbol = request.form.get("symbol").upper()
        
        # Look up the stock symbol by calling the loookyp function
        getQuote = getData(symbol)      
        
        # If lookup is unsuccessful, function returns None
        if not symbol:
            return apology("Please enter a stock symbol", 400)
        
        elif not getQuote:
            return apology("No stock found", 400)
        
        # If lookup is successful, function returns a dictionary with name, price, symbol
        else:
            # Display the results (see helpers.py)
            name = getQuote["name"]
            price = getQuote["price"]
        
            return render_template("quoted.html", name=name, price=price, symbol=symbol.upper())
    
    # When requested via GET, display form to request a stock quote
    return render_template("quote.html")


# ------------------------------------------------------------------
# Register & Login
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            # return apology("must provide username", 403)
            print("no username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            # return apology("must provide password", 403)
            print("no password")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            # return apology("invalid username and/or password", 403)
            print("invalid username or password")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # Forget any user_id
    session.clear()
    
    # When requested via GET, should display registration form
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_pw = request.form.get("confirmation")

        # Ensure username was submitted
        if not username:
            # return apology("Please provide username", 400)
            print("no username")

        # Ensure password was submitted
        elif not password:
            # return apology("Please provide password", 400)
            print("no password")
          
        # Ensure min length of password is satisfied
        # elif len(password) < 6:
        #     # return apology("Password must have at least 6 characters", 400)
        #     print("len(password) < 6")
            
        # Ensure password (again) was submitted
        elif not confirm_pw:
            # return apology("Please confirm the password", 400)
            print("no confirmation password")
            
        # Ensure the typed password is same as password (again)
        elif password != confirm_pw:
            # return apology("Mismatch password", 400)
            print("wrong confirmation password")
            
        else:
            # Check if user name is already exist
            check_user = db.execute("SELECT username FROM users WHERE username=:username", 
                                    username=request.form.get("username"))
            if len(check_user) == 1:
                # return apology("Username already exists", 400)
                print("account alredy exist")
                
            else:
                # Create database for username
                # Hash the user's password
                add_user = db.execute("INSERT INTO users (username, hash) VALUES (:username, :password)", 
                                        username=request.form.get("username"), 
                                        password=generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8))
                # Flash for success registered
                # flash("Registered")
                return redirect("/")
            
    return render_template("register.html")

# ------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)
