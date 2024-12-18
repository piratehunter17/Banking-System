from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# SQLite database connection function
def get_db_connection():
    conn = sqlite3.connect('techstar_bank.db')
    conn.row_factory = sqlite3.Row
    return conn

# Create tables if they don't exist
def create_tables():
    conn = get_db_connection()
    # Remove balance from user, it's tracked per transaction now
    conn.execute('''CREATE TABLE IF NOT EXISTS user (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        debit_card TEXT UNIQUE NOT NULL,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        role TEXT DEFAULT 'user')''')
    
    # Add balance to each transaction record
    conn.execute('''CREATE TABLE IF NOT EXISTS transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        transaction_type TEXT NOT NULL,
                        amount REAL NOT NULL,
                        balance REAL NOT NULL,
                        recipient_id INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES user (id),
                        FOREIGN KEY (recipient_id) REFERENCES user (id))''')
    conn.commit()
    conn.close()

# Run the table creation
create_tables()

# Home Route
@app.route('/')
def home():
    return render_template('home.html')

# Registration Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['firstName']
        debit_card = request.form['debitCardNumber'].replace(" ", "")
        username = request.form['newUsername']
        password = request.form['newPassword']
        role = request.form['role']

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO user (name, debit_card, username, password, role) VALUES (?, ?, ?, ?, ?)',
                         (name, debit_card, username, password, role))
            conn.commit()
            flash('Account created successfully! You can now log in.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or debit card number already exists.')
        finally:
            conn.close()

    return render_template('register.html')

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM user WHERE username = ? AND password = ?', (username, password)).fetchone()
        conn.close()

        if user:
            session['loggedin'] = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']

            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid login credentials.')
    return render_template('login.html')

# User Dashboard Route
@app.route('/user/dashboard')
def user_dashboard():
    if 'loggedin' in session and session['role'] == 'user':
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM user WHERE id = ?', (session['user_id'],)).fetchone()

        # Get the current balance by summing all the user's transactions
        balance = conn.execute('SELECT SUM(amount) as balance FROM transactions WHERE user_id = ?', (session['user_id'],)).fetchone()['balance']
        conn.close()

        return render_template('user/dashboard.html', user=user, balance=balance)
    return redirect(url_for('login'))

# Admin Dashboard Route
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'loggedin' in session and session['role'] == 'admin':
        conn = get_db_connection()
        users = conn.execute('SELECT * FROM user').fetchall()
        conn.close()
        return render_template('admin/dashboard.html', users=users)
    return redirect(url_for('login'))

# Logout Route
@app.route('/logout')
def logout():
    session.clear() 
    return redirect(url_for('login'))  

# Deposit Route
@app.route('/user/dashboard/deposit', methods=['GET', 'POST'])
def deposit():
    if 'loggedin' in session and session['role'] == 'user':
        if request.method == 'POST':
            amount = float(request.form['amount'])
            user_id = session['user_id']

            conn = get_db_connection()
            # Get the current balance and update it
            current_balance = conn.execute('SELECT SUM(amount) as balance FROM transactions WHERE user_id = ?', (user_id,)).fetchone()['balance'] or 0
            new_balance = current_balance + amount

            conn.execute('INSERT INTO transactions (user_id, transaction_type, amount, balance) VALUES (?, ?, ?, ?)', 
                         (user_id, 'deposit', amount, new_balance))
            conn.commit()
            conn.close()

            flash(f'Deposited ${amount}')
            return redirect(url_for('user_dashboard'))

        return render_template('user/dashboard/deposit.html')

# Transfer Route
@app.route('/user/dashboard/transfer', methods=['GET', 'POST'])
def transfer():
    if 'loggedin' in session and session['role'] == 'user':
        if request.method == 'POST':
            sender_id = session['user_id']
            receiver_username = request.form['receiver']
            amount = float(request.form['amount'])

            conn = get_db_connection()
            sender = conn.execute('SELECT * FROM user WHERE id = ?', (sender_id,)).fetchone()
            receiver = conn.execute('SELECT * FROM user WHERE username = ?', (receiver_username,)).fetchone()

            if receiver:
                # Get sender's current balance
                current_balance = conn.execute('SELECT SUM(amount) as balance FROM transactions WHERE user_id = ?', (sender_id,)).fetchone()['balance'] or 0

                if current_balance >= amount:
                    # Update sender's balance
                    new_balance = current_balance - amount
                    conn.execute('INSERT INTO transactions (user_id, transaction_type, amount, balance, recipient_id) VALUES (?, ?, ?, ?, ?)',
                                 (sender_id, 'transfer', -amount, new_balance, receiver['id']))

                    # Update receiver's balance
                    receiver_balance = conn.execute('SELECT SUM(amount) as balance FROM transactions WHERE user_id = ?', (receiver['id'],)).fetchone()['balance'] or 0
                    new_receiver_balance = receiver_balance + amount
                    conn.execute('INSERT INTO transactions (user_id, transaction_type, amount, balance) VALUES (?, ?, ?, ?)',
                                 (receiver['id'], 'receive', amount, new_receiver_balance))

                    conn.commit()
                    flash(f'Transferred ${amount} to {receiver_username}')
                else:
                    flash('Insufficient balance.')
            else:
                flash('Recipient not found.')

            conn.close()
            return redirect(url_for('user_dashboard'))

        return render_template('user/dashboard/transfer.html')

# Transaction History Route
@app.route('/user/dashboard/transhistory')
def transhistory():
    if 'loggedin' in session and session['role'] == 'user':
        conn = get_db_connection()
        transactions = conn.execute('''
            SELECT 
                t.transaction_type, 
                t.amount, 
                u_recipient.username AS recipient, 
                t.balance, 
                t.created_at
            FROM transactions t
            LEFT JOIN user u_recipient ON t.recipient_id = u_recipient.id
            WHERE t.user_id = ?
            ORDER BY t.created_at DESC
        ''', (session['user_id'],)).fetchall()

        conn.close()
        return render_template('user/dashboard/transhistory.html', transactions=transactions)
    return redirect(url_for('login'))

# Withdraw Route
@app.route('/user/dashboard/withdraw', methods=['GET', 'POST'])
def withdraw():
    if 'loggedin' in session and session['role'] == 'user':
        if request.method == 'POST':
            amount = float(request.form['amount'])
            user_id = session['user_id']

            conn = get_db_connection()
            current_balance = conn.execute('SELECT SUM(amount) as balance FROM transactions WHERE user_id = ?', (user_id,)).fetchone()['balance'] or 0

            if current_balance >= amount:
                new_balance = current_balance - amount
                conn.execute('INSERT INTO transactions (user_id, transaction_type, amount, balance) VALUES (?, ?, ?, ?)', 
                             (user_id, 'withdraw', -amount, new_balance))
                conn.commit()
                flash(f'Withdrew ${amount}')
            else:
                flash('Insufficient balance.')

            conn.close()
            return redirect(url_for('user_dashboard'))

        return render_template('user/dashboard/withdraw.html')

if __name__ == '__main__':
    app.run(debug=True, port=5500)
