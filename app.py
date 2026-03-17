from flask import Flask, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)

# Create users text file 
USER_DB = "users.txt"
if not os.path.exists(USER_DB):
    with open(USER_DB, "w") as f:
        f.write("admin,admin123,true\n")

@app.route('/')
def index():
    # Check login status from cookie
    logged_in = request.cookies.get('logged_in')
    username = request.cookies.get('username', '')
    
    if logged_in == 'yes':
        return f"""
        <h1>Welcome {username}!</h1>
        <p>You are logged in</p>
        <a href='/logout'>Logout</a>
        <br><br>
        <a href='/balance'>Check Balance</a>
        """
    return """
    <h1>Welcome to LSU Banking</h1>
    <a href='/login'>Login</a>
    """

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get form data
        username = request.form['username']
        password = request.form['password']
        
        # Check credentials against text file
        with open(USER_DB, "r") as f:
            for line in f:
                stored_user, stored_pass, is_admin = line.strip().split(',')
                if username == stored_user and password == stored_pass:
                    # Set cookies for login state
                    response = redirect(url_for('index'))
                    response.set_cookie('logged_in', 'yes')
                    response.set_cookie('username', username)
                    response.set_cookie('is_admin', is_admin)
                    return response
        
        return "<h1>Login Failed</h1><a href='/login'>Try again</a>"
    
    # Display login form
    return """
    <form method='POST'>
        <input type='text' name='username' placeholder='Username'><br>
        <input type='password' name='password' placeholder='Password'><br>
        <button type='submit'>Login</button>
    </form>
    <p>Test account: admin / admin123</p>
    """

@app.route('/logout')
def logout():
    # Clear cookies to log out
    response = redirect(url_for('index'))
    response.set_cookie('logged_in', '', expires=0)
    response.set_cookie('username', '', expires=0)
    response.set_cookie('is_admin', '', expires=0)
    return response

@app.route('/balance')
def balance():
    # Verify user is logged in
    if request.cookies.get('logged_in') != 'yes':
        return "<h1>Not logged in!</h1><a href='/login'>Login</a>"
    
    username = request.cookies.get('username')
    # Get balance from URL parameter
    balance = request.args.get('amount', '$1000')
    
    return f"""
    <h1>Account Balance</h1>
    <p>User: {username}</p>
    <p>Balance: {balance}</p>
    <a href='/'>Home</a>
    """

@app.route('/admin')
def admin():
    # Check if user is admin via cookie
    if request.cookies.get('is_admin') == 'true':
        # Read all users from file
        users = ""
        with open(USER_DB, "r") as f:
            users = f.read().replace('\n', '<br>')
        
        return f"""
        <h1>Admin Panel</h1>
        <h2>All Users:</h2>
        <p>{users}</p>
        <h2>Cookies:</h2>
        <p>{request.cookies}</p>
        """
    return "<h1>Access Denied</h1>"

if __name__ == '__main__':
    app.run(debug=True)