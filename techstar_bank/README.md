techstar_bank/
│
├── static/
│   ├── logoo.png            # Bank logo
│   ├── user.png             # User icon
│
├── templates/
│   ├── admin/
│   │   └── dashboard.html   # Admin dashboard page
│   ├── user/
│   │   ├── dashboard/       # User dashboard page
│   │   │   ├── deposit.html        # Deposit form
│   │   │   ├── transfer.html       # Transfer form
│   │   │   ├── transhistory.html   # Transaction history page
│   │   │   ├── withdraw.html       # Withdraw form
│   │   └── dashboard.html          # User dashboard
│   ├── home.html            # Homepage 
│   ├── login.html           # Login page
│   ├── register.html        # Registration page
│
├── techstar_bank.db          # SQLite database for storing user data and transactions
├── app.py                    # Main application logic



Steps to run the project:

Step 1 : Extract the ZIP file
Step 2 : Navigate to tecstar_bank directory
Step 3 : Install requirements.txt by running the command "pip install -r requirements.txt" in the terminal
Step 4 : Install sqlite3 for your respective OS from "https://www.sqlite.org/download.html"
Step 5 : Run the command "python app.py" in the terminal
Step 6 : Open your browser and navigate to "http://127.0.0.1:5500"