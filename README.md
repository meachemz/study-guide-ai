# 🚀 Running the Django Server

This guide walks you through setting up and running the Django development server using a virtual environment and project dependencies.

---

## 🧰 Prerequisites

- Python
- Git 
- Virtual environment setup (via `activate.sh`)
- `requirements.txt` file in the root directory

---

## ⚙️ Setup Instructions

### 1. Clone the Repository 
### 2. Activate Enviorment using the provided shell script to activate your environment 
source activate.sh
### 3. Install Dependencies
pip install -r requirements.txt
### 4. Start the Server to see on your local machine
python manage.py runserver




# Accessing the Production Database (Render) Locally

To run Django management commands (`createsuperuser`, `changepassword`, `shell`, etc.) against live database on Render, need to temporarily tell your local machine to connect to it instead of your local `db.sqlite3` file.

## Steps

1.  **Get the External Database URL:**
    * Go to your Render Dashboard.
    * Click on your **PostgreSQL database** service.
    * Scroll down to the "Connections" section.
    * Copy the **External Database URL**. It looks like `postgres://...`.
        

2.  **Open Your Local Terminal:**
    * Open a terminal window on your computer.
    * Navigate (`cd`) to your project's root directory (the one containing `manage.py`).

3.  **Set the `DATABASE_URL` Environment Variable:**
    * Paste the **External Database URL** you copied into the command below. Make sure it's inside **double quotes**.
    * Run the command appropriate for your terminal:

        * **Git Bash / macOS / Linux (use `export`):**
            ```bash
            export DATABASE_URL="YOUR_EXTERNAL_DATABASE_URL_HERE"
            ```

        * **Windows Command Prompt (CMD) (use `set`):**
            ```cmd
            set DATABASE_URL="YOUR_EXTERNAL_DATABASE_URL_HERE"
            ```

        * **Windows PowerShell (use `$env:`):**
            ```powershell
            $env:DATABASE_URL="YOUR_EXTERNAL_DATABASE_URL_HERE"
            ```
    * **Important:** This variable is **temporary** and only exists for this specific terminal session.

4.  **Confirm the Variable is Set (Optional but Recommended):**
    * To make sure the variable was set correctly, run the `echo` command for your terminal:

        * **Git Bash / macOS / Linux:**
            ```bash
            echo $DATABASE_URL
            ```

        * **Windows Command Prompt (CMD):**
            ```cmd
            echo %DATABASE_URL%
            ```

        * **Windows PowerShell:**
            ```powershell
            echo $env:DATABASE_URL
            ```
    * This should print the full `postgres://...` URL you just set. If it doesn't, check the command syntax in Step 3 again. ✅

5.  **Run Your Django Command:**
    * **In the same terminal window**, run the management command you need. Examples:
        ```bash
        # Create a new admin user
        python manage.py createsuperuser

        # Change an existing user's password
        python manage.py changepassword <username>

        # Open the Django shell connected to the production DB
        python manage.py shell
        ```

6.  **Finish:** Once you're done, simply **close the terminal window**. The `DATABASE_URL` variable will be unset, and your local environment will go back to using `db.sqlite3`.
