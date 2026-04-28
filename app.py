from flask import Flask, request, redirect, url_for, render_template, session
import os
import random
import secrets
from datetime import datetime, timedelta

app = Flask(__name__)

# Database file paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_DB = os.path.join(BASE_DIR, "users.txt")
ACCOUNT_DB = os.path.join(BASE_DIR, "accounts.txt")
TRANSACTION_DB = os.path.join(BASE_DIR, "transactions.txt")

# secret.key file path & generation if it does not exist, 
# required when using sessions via Flask instead of cookies
KEY_FILE = os.path.join(BASE_DIR, 'secret.key')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

if os.path.exists(KEY_FILE):
    with open(KEY_FILE, 'r') as f:
        app.config['SECRET_KEY'] = f.read().strip()
else:
    new_key = secrets.token_hex(32)
    with open(KEY_FILE, 'w') as f:
        f.write(new_key)
    app.config['SECRET_KEY'] = new_key

def initialize_database():
    """Create database files with default admin account"""
    if not os.path.exists(USER_DB):
        with open(USER_DB, 'w') as f:
            f.write("admin,admin123,System Administrator,admin@lsu.edu,true\n")
    else:
        with open(USER_DB, 'r') as f:
            content = f.read()
            if 'admin' not in content:
                with open(USER_DB, 'a') as f2:
                    f2.write("admin,admin123,System Administrator,admin@lsu.edu,true\n")
    
    if not os.path.exists(ACCOUNT_DB):
        with open(ACCOUNT_DB, 'w') as f:
            f.write("ACC10000,1000000.00,admin\n")
    else:
        admin_has_account = False
        with open(ACCOUNT_DB, 'r') as f:
            for line in f:
                if 'admin' in line:
                    admin_has_account = True
                    break
        if not admin_has_account:
            with open(ACCOUNT_DB, 'a') as f2:
                f2.write("ACC10000,1000000.00,admin\n")
    
    if not os.path.exists(TRANSACTION_DB):
        with open(TRANSACTION_DB, 'w') as f:
            f.write("")

def generate_account_number():
    """Generate unique 10-digit account number"""
    existing_numbers = []
    if os.path.exists(ACCOUNT_DB):
        with open(ACCOUNT_DB, 'r') as f:
            for line in f:
                if line.strip():
                    parts = line.split(',')
                    if len(parts) >= 1:
                        existing_numbers.append(parts[0])
    
    while True:
        num = f"ACC{random.randint(10000, 99999)}"
        if num not in existing_numbers:
            return num

def get_account_owner(account_number):
    """Get username of account owner"""
    if not os.path.exists(ACCOUNT_DB):
        return None
    
    with open(ACCOUNT_DB, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split(',')
                if len(parts) >= 3 and parts[0] == account_number:
                    return parts[2]
    return None

def parse_csv_field(field):
    """Parse an escaped CSV field, handling quoted values"""
    field = field.strip()
    if field.startswith('"') and field.endswith('"'):
        # Unwrap and unescape
        inner = field[1:-1]
        # Unescape double quotes
        return inner.replace('""', '"')
    return field

def get_user(username):
    """Retrieve user data by username"""
    if not os.path.exists(USER_DB):
        return None
    
    with open(USER_DB, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                # Simple CSV parsing - split by comma but handle quoted fields
                parts = []
                current = ""
                in_quotes = False
                for char in line:
                    if char == '"':
                        in_quotes = not in_quotes
                        current += char
                    elif char == ',' and not in_quotes:
                        parts.append(current)
                        current = ""
                    else:
                        current += char
                parts.append(current)  # Add last field
                
                if len(parts) >= 5 and parse_csv_field(parts[0]) == username:
                    return {
                        'username': parse_csv_field(parts[0]),
                        'password': parse_csv_field(parts[1]),
                        'full_name': parse_csv_field(parts[2]),
                        'email': parse_csv_field(parts[3]),
                        'is_admin': parse_csv_field(parts[4])
                    }
    return None

def get_user_accounts(username):
    """Get all accounts belonging to a user"""
    accounts = []
    if not os.path.exists(ACCOUNT_DB):
        return accounts
    
    with open(ACCOUNT_DB, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split(',')
                if len(parts) >= 3 and parts[2] == username:
                    accounts.append({
                        'account_number': parts[0],
                        'balance': float(parts[1]),
                        'owner': parts[2]
                    })
    return accounts

def get_all_accounts():
    """Get all accounts in the system"""
    accounts = []
    if not os.path.exists(ACCOUNT_DB):
        return accounts
    
    with open(ACCOUNT_DB, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split(',')
                if len(parts) >= 3:
                    accounts.append({
                        'account_number': parts[0],
                        'balance': float(parts[1]),
                        'owner': parts[2]
                    })
    return accounts

def get_all_users_with_balance():
    """Get all users with total account balance"""
    users = []
    if not os.path.exists(USER_DB):
        return users
    
    with open(USER_DB, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                # Use CSV parsing to handle escaped fields
                parts = []
                current = ""
                in_quotes = False
                for char in line:
                    if char == '"':
                        in_quotes = not in_quotes
                        current += char
                    elif char == ',' and not in_quotes:
                        parts.append(current)
                        current = ""
                    else:
                        current += char
                parts.append(current)
                
                if len(parts) >= 5:
                    username = parse_csv_field(parts[0])
                    accounts = get_user_accounts(username)
                    total_balance = sum(acc['balance'] for acc in accounts)
                    users.append({
                        'username': username,
                        'full_name': parse_csv_field(parts[2]),
                        'email': parse_csv_field(parts[3]),
                        'is_admin': parse_csv_field(parts[4]),
                        'account_count': len(accounts),
                        'total_balance': total_balance
                    })
    return users

def add_transaction(from_acc, to_acc, amount, description):
    """Record a transaction in the log"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(TRANSACTION_DB, 'a') as f:
        f.write(f"{from_acc},{to_acc},{amount},{description},{timestamp}\n")

def get_user_transactions(username):
    """Get all transactions for a specific user"""
    transactions = []
    user_accounts = get_user_accounts(username)
    user_account_numbers = [acc['account_number'] for acc in user_accounts]
    
    if not os.path.exists(TRANSACTION_DB):
        return transactions
    
    with open(TRANSACTION_DB, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split(',')
                if len(parts) == 5:
                    from_acc, to_acc, amount, description, timestamp = parts
                    if from_acc in user_account_numbers or to_acc in user_account_numbers:
                        from_owner = get_account_owner(from_acc)
                        to_owner = get_account_owner(to_acc)
                        transactions.append({
                            'from': from_acc,
                            'to': to_acc,
                            'amount': float(amount),
                            'description': description,
                            'timestamp': timestamp,
                            'is_sent': from_acc in user_account_numbers,
                            'from_owner': from_owner,
                            'to_owner': to_owner
                        })
    
    return sorted(transactions, key=lambda x: x['timestamp'], reverse=True)

def get_all_transactions():
    """Get all transactions in the system"""
    transactions = []
    if not os.path.exists(TRANSACTION_DB):
        return transactions
    
    with open(TRANSACTION_DB, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split(',')
                if len(parts) == 5:
                    from_acc, to_acc, amount, description, timestamp = parts
                    from_owner = get_account_owner(from_acc)
                    to_owner = get_account_owner(to_acc)
                    transactions.append({
                        'from': from_acc,
                        'to': to_acc,
                        'amount': float(amount),
                        'description': description,
                        'timestamp': timestamp,
                        'from_owner': from_owner,
                        'to_owner': to_owner
                    })
    
    return sorted(transactions, key=lambda x: x['timestamp'], reverse=True)

def update_account_balance(account_number, new_balance):
    """Update balance for a specific account"""
    lines = []
    with open(ACCOUNT_DB, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split(',')
                if len(parts) == 3:
                    if parts[0] == account_number:
                        lines.append(f"{parts[0]},{new_balance},{parts[2]}\n")
                    else:
                        lines.append(f"{parts[0]},{parts[1]},{parts[2]}\n")
    
    with open(ACCOUNT_DB, 'w') as f:
        f.writelines(lines)

def show_message_page(message, redirect_url, redirect_text):
    """Display styled message page with purple button"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>LSU Banking</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #461d7c 0%, #fdd023 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }}
            
            .message-container {{
                max-width: 500px;
                width: 100%;
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                padding: 2rem;
                text-align: center;
            }}
            
            .message-icon {{
                font-size: 4rem;
                margin-bottom: 1rem;
            }}
            
            .message-title {{
                font-size: 1.5rem;
                color: #461d7c;
                margin-bottom: 1rem;
            }}
            
            .message-text {{
                color: #666;
                margin-bottom: 2rem;
                font-size: 1.1rem;
            }}
            
            .btn {{
                display: inline-block;
                padding: 1rem 2rem;
                border-radius: 10px;
                text-decoration: none;
                font-weight: 600;
                font-size: 1.1rem;
                transition: all 0.3s;
                border: none;
                cursor: pointer;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                background: linear-gradient(135deg, #461d7c 0%, #5a2d9e 100%);
                color: white;
            }}
            
            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 12px rgba(0,0,0,0.2);
            }}
        </style>
    </head>
    <body>
        <div class="message-container">
            <div class="message-icon">ℹ️</div>
            <div class="message-title">Notice</div>
            <div class="message-text">{message}</div>
            <a href="{redirect_url}" class="btn">{redirect_text}</a>
        </div>
    </body>
    </html>
    """

# Initialize database on startup
initialize_database()

# Routes
@app.route('/')
def index():
    """Display homepage"""
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def escape_csv_field(field):
    """Escape commas and quotes in CSV fields to prevent injection"""
    if ',' in field or '"' in field or '\n' in field:
        # Wrap in quotes and escape existing quotes
        return '"' + field.replace('"', '""') + '"'
    return field

def register():
    """Handle user registration"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        full_name = request.form['full_name']
        
        if get_user(username):
            return show_message_page(
                "Username already exists. Please choose a different username.",
                "/register",
                "Try Again"
            )
        
        # Escape CSV fields to prevent injection attacks
        escaped_username = escape_csv_field(username)
        escaped_password = escape_csv_field(password)
        escaped_full_name = escape_csv_field(full_name)
        escaped_email = escape_csv_field(email)
        
        with open(USER_DB, 'a') as f:
            f.write(f"{escaped_username},{escaped_password},{escaped_full_name},{escaped_email},false\n")
        
        account_num = generate_account_number()
        with open(ACCOUNT_DB, 'a') as f:
            f.write(f"{account_num},1000.00,{username}\n")
        
        return show_message_page(
            "Account created successfully! You can now log in.",
            "/login",
            "Proceed to Login"
        )
    
    return render_template('register.html', session=session)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = get_user(username)
        
        if user and user['password'] == password:
            session['logged_in'] = True
            session['username'] = username
            session['is_admin'] = user['is_admin']

            resp = redirect(url_for('dashboard'))
            return resp
        else:
            return show_message_page(
                "Invalid username or password. Please try again.",
                "/login",
                "Try Again"
            )
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    """Display user dashboard with accounts and recent transactions"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    username = session.get('username')

    user = get_user(username)
    accounts = get_user_accounts(username)
    transactions = get_user_transactions(username)
    
    return render_template('dashboard.html', 
                         user=user,
                         accounts=accounts,
                         transactions=transactions)

@app.route('/transfer', methods=['GET', 'POST'])
def transfer():
    """Handle money transfers (regular users see only their accounts, admins see all)"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    username = session.get('username')
    is_admin = session.get('is_admin') == 'true'
    
    if is_admin:
        from_accounts = get_all_accounts()
    else:
        from_accounts = get_user_accounts(username)
    
    if request.method == 'POST':
        from_account = request.form['from_account']
        to_account = request.form['to_account']
        amount = float(request.form['amount'])
        description = request.form.get('description', 'Transfer')
        
        if not is_admin:
            user_accounts = get_user_accounts(username)
            user_account_numbers = [acc['account_number'] for acc in user_accounts]
            if from_account not in user_account_numbers:
                return show_message_page(
                    "You don't have permission to transfer from this account.",
                    "/transfer",
                    "Go Back"
                )
        
        all_accounts = get_all_accounts()
        source_account = next((acc for acc in all_accounts if acc['account_number'] == from_account), None)
        dest_account = next((acc for acc in all_accounts if acc['account_number'] == to_account), None)
        
        if not source_account:
            return show_message_page("Source account not found.", "/transfer", "Go Back")
        
        if not dest_account:
            return show_message_page("Destination account not found.", "/transfer", "Go Back")
        
        if source_account['balance'] < amount:
            return show_message_page(
                f"Insufficient funds. Available: ${source_account['balance']:.2f}",
                "/transfer",
                "Go Back"
            )
        
        update_account_balance(from_account, source_account['balance'] - amount)
        update_account_balance(to_account, dest_account['balance'] + amount)
        add_transaction(from_account, to_account, amount, description)
        
        return show_message_page(
            f"Successfully transferred ${amount:.2f} to {to_account}",
            "/transfer",
            "Make Another Transfer"
        )
    
    return render_template('transfer.html',
                         session=session,
                         accounts=from_accounts,
                         is_admin=is_admin)

@app.route('/transactions')
def transactions_page():
    """Display transaction history with search and view toggle for admin"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    username = session.get('username')
    is_admin = session.get('is_admin') == 'true'
    view_type = request.args.get('view', 'personal')
    search_query = request.args.get('search', '')
    
    if is_admin and view_type == 'all':
        transactions_list = get_all_transactions()
    else:
        transactions_list = get_user_transactions(username)
    
    if search_query:
        transactions_list = [t for t in transactions_list if search_query.lower() in t['description'].lower()]
    
    return render_template('transactions.html',
                         session=session,
                         transactions=transactions_list,
                         search_query=search_query,
                         is_admin=is_admin,
                         view_type=view_type)

@app.route('/admin')
def admin():
    """Display admin dashboard with system overview"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    if session.get('is_admin') != 'true':
        return show_message_page(
            "Access Denied. Admin privileges required.",
            "/dashboard",
            "Return to Dashboard"
        ), 403
    
    users = get_all_users_with_balance()
    accounts = get_all_accounts()
    transactions = get_all_transactions()
    total_balance = sum(acc['balance'] for acc in accounts)
    
    return render_template('admin.html',
                         users=users,
                         accounts=accounts,
                         transactions=transactions,
                         total_balance=total_balance)

@app.route('/admin_transfer', methods=['GET', 'POST'])
def admin_transfer():
    """Admin-only route for transferring from any account"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    if session.get('is_admin') != 'true':
        return show_message_page(
            "Access Denied. Admin privileges required.",
            "/dashboard",
            "Return to Dashboard"
        ), 403
    
    all_accounts = get_all_accounts()
    
    if request.method == 'POST':
        from_account = request.form['from_account']
        to_account = request.form['to_account']
        amount = float(request.form['amount'])
        description = request.form.get('description', 'Admin Transfer')
        
        source_account = next((acc for acc in all_accounts if acc['account_number'] == from_account), None)
        dest_account = next((acc for acc in all_accounts if acc['account_number'] == to_account), None)
        
        if not source_account:
            return show_message_page("Source account not found.", "/admin_transfer", "Go Back")
        
        if not dest_account:
            return show_message_page("Destination account not found.", "/admin_transfer", "Go Back")
        
        if source_account['balance'] < amount:
            return show_message_page(
                f"Insufficient funds. Available: ${source_account['balance']:.2f}",
                "/admin_transfer",
                "Go Back"
            )
        
        update_account_balance(from_account, source_account['balance'] - amount)
        update_account_balance(to_account, dest_account['balance'] + amount)
        add_transaction(from_account, to_account, amount, description)
        
        return show_message_page(
            f"Transferred ${amount:.2f} from {source_account['owner']} to {dest_account['owner']}",
            "/admin_transfer",
            "Make Another Transfer"
        )
    
    return render_template('admin_transfer.html',
                         session=session,
                         accounts=all_accounts)

@app.route('/logout')
def logout():
    """Clear session cookies and log out user"""
    session.clear()

    resp = redirect(url_for('index'))
    return resp

if __name__ == '__main__':
    app.run(debug=True, port=5000)
