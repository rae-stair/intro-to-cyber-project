import os
import re
import sqlite3
import datetime
from flask import (
    Flask, flash, redirect, render_template, request,
    send_from_directory, session, url_for
)
from werkzeug.security import generate_password_hash, check_password_hash

# ------------------------------
# PATHS / DB
# ------------------------------

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(ROOT_DIR, "db", "library.db")
PROJECT_FRONT_CSS = os.path.join(ROOT_DIR, "static", "css")
PROJECT_FRONT_JS = os.path.join(ROOT_DIR, "static", "js")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_ip():
    return request.remote_addr or "unknown"

# ------------------------------
# BRUTE FORCE / COOLDOWN
# ------------------------------

MAX_FAILED_ATTEMPTS = 5
COOLDOWN_SECONDS = 120  # 2 minutes

def get_attempts(ip):
    db = get_db()
    row = db.execute(
        "SELECT attempts, last_attempt FROM login_attempts WHERE ip = ?",
        (ip,)
    ).fetchone()
    if row:
        return row["attempts"], row["last_attempt"]
    return 0, None

def parse_sqlite_timestamp(ts):
    if not ts:
        return None
    try:
        return datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        return datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")

def increment_attempts(ip):
    db = get_db()
    row = db.execute(
        "SELECT attempts FROM login_attempts WHERE ip = ?", (ip,)
    ).fetchone()

    if row:
        db.execute(
            "UPDATE login_attempts "
            "SET attempts = attempts + 1, last_attempt = CURRENT_TIMESTAMP "
            "WHERE ip = ?",
            (ip,)
        )
    else:
        db.execute(
            "INSERT INTO login_attempts (ip, attempts, last_attempt) "
            "VALUES (?, 1, CURRENT_TIMESTAMP)",
            (ip,)
        )
    db.commit()

def reset_attempts(ip):
    db = get_db()
    db.execute("DELETE FROM login_attempts WHERE ip = ?", (ip,))
    db.commit()

def is_cooldown_over(last_attempt):
    if not last_attempt:
        return True
    last = parse_sqlite_timestamp(last_attempt)
    now = datetime.datetime.now()
    return (now - last).total_seconds() >= COOLDOWN_SECONDS

# ------------------------------
# DEV AUTH HELPERS
# ------------------------------

DEV_ROLES = {"admin", "customer"}

def _dev_skip_login_enabled():
    return True  # always allow for your project

def _session_has_auth():
    return bool(session.get("dev_skip_auth"))

def _dev_role_ok(role):
    return _session_has_auth() and session.get("dev_role") == role

# ------------------------------
# FLASK APP
# ------------------------------

app = Flask(__name__, template_folder="html", static_folder="static")
app.secret_key = "supersecretdevkey123"

# ------------------------------
# DEV ROUTES
# ------------------------------

@app.get("/dev/skip-login/<role>")
def dev_skip_login(role):
    if role not in DEV_ROLES:
        flash("Invalid dev role.", "error")
        return redirect(url_for("login"))

    session["dev_skip_auth"] = True
    session["dev_role"] = role

    if role == "customer":
        session["patron_id"] = 1
        return redirect(url_for("customer_home"))
    else:
        session.pop("patron_id", None)
        return redirect(url_for("admin_dashboard"))

@app.get("/dev/logout")
def dev_logout():
    session.clear()
    return redirect(url_for("login"))

# ------------------------------
# LOGIN ROUTES
# ------------------------------

@app.route("/")
def home():
    return redirect(url_for("login"))

@app.get("/login")
def login():
    return render_template("login.html")

@app.post("/login")
def login_post():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    ip = get_ip()

    # FORCE increment on ANY invalid submission
    if not username or not password:
        increment_attempts(ip)
        flash("Username and password are required.", "error")
        return redirect(url_for("login"))

    failed_attempts, last_attempt = get_attempts(ip)

    # LOCKOUT CHECK
    if failed_attempts >= MAX_FAILED_ATTEMPTS:
        if is_cooldown_over(last_attempt):
            reset_attempts(ip)
        else:
            last = parse_sqlite_timestamp(last_attempt)
            now = datetime.datetime.now()
            elapsed = int((now - last).total_seconds())
            remaining = COOLDOWN_SECONDS - elapsed
            if remaining < 0:
                remaining = 0
            flash(f"Too many failed attempts. Try again in {remaining} seconds.", "error")
            return redirect(url_for("login"))

    db = get_db()

    # ADMIN LOGIN
    admin = db.execute(
        "SELECT id, name, password FROM admins WHERE name = ?",
        (username,)
    ).fetchone()

    if admin:
        if check_password_hash(admin["password"], password):
            reset_attempts(ip)
            session["dev_skip_auth"] = True
            session["dev_role"] = "admin"
            session.pop("patron_id", None)
            return redirect(url_for("admin_dashboard"))

        increment_attempts(ip)
        flash("Incorrect password for admin account.", "error")
        return redirect(url_for("login"))

    # PATRON LOGIN
    patron = db.execute(
        "SELECT id, name, email, password FROM patrons WHERE name = ? OR email = ?",
        (username, username)
    ).fetchone()

    if patron:
        if check_password_hash(patron["password"], password):
            reset_attempts(ip)
            session["dev_skip_auth"] = True
            session["dev_role"] = "customer"
            session["patron_id"] = patron["id"]
            return redirect(url_for("customer_home"))

        increment_attempts(ip)
        flash("Incorrect password for patron account.", "error")
        return redirect(url_for("login"))

    # NO ACCOUNT FOUND
    increment_attempts(ip)
    flash("No matching account found.", "error")
    return redirect(url_for("login"))

@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ------------------------------
# STATIC ROUTES
# ------------------------------

@app.get("/_pf/css/<path:filename>")
def project_front_css(filename):
    return send_from_directory(PROJECT_FRONT_CSS, filename)

@app.get("/_pf/js/<path:filename>")
def project_front_js(filename):
    return send_from_directory(PROJECT_FRONT_JS, filename)

# ------------------------------
# ADMIN ROUTES
# ------------------------------

@app.get("/admin")
def admin_dashboard():
    if not _dev_role_ok("admin"):
        flash("Admin role required.", "error")
        return redirect(url_for("login"))

    db = get_db()

    overdue = db.execute(
        """
        SELECT patrons.name, patrons.phone, books.title, books.id AS book_id,
               checkouts.due_date,
               CAST((julianday('now') - julianday(checkouts.due_date)) AS INT) AS days_overdue
        FROM checkouts
        JOIN patrons ON patrons.id = checkouts.patron_id
        JOIN books ON books.id = checkouts.book_id
        WHERE checkouts.returned = 0
          AND checkouts.due_date < date('now')
        ORDER BY days_overdue DESC
        """
    ).fetchall()

    patrons_raw = db.execute(
        "SELECT id, name, email, phone FROM patrons ORDER BY id"
    ).fetchall()

    patrons = []
    for p in patrons_raw:
        books_out = db.execute(
            """
            SELECT books.title, books.status
            FROM checkouts
            JOIN books ON books.id = checkouts.book_id
            WHERE checkouts.patron_id = ?
              AND checkouts.returned = 0
            """,
            (p["id"],)
        ).fetchall()
        patrons.append({
            "name": p["name"],
            "email": p["email"],
            "phone": p["phone"],
            "books": books_out
        })

    total_books = db.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    total_patrons = db.execute("SELECT COUNT(*) FROM patrons").fetchone()[0]
    checked_out = db.execute(
        "SELECT COUNT(*) FROM books WHERE status='checked_out'"
    ).fetchone()[0]

    return render_template(
        "admin.html",
        overdue=overdue,
        patrons=patrons,
        total_books=total_books,
        total_patrons=total_patrons,
        checked_out=checked_out
    )

@app.post("/admin/add-patron")
def admin_add_patron():
    if not _dev_role_ok("admin"):
        flash("Admin role required.", "error")
        return redirect(url_for("login"))

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    password = request.form.get("password", "").strip()
    confirm_password = request.form.get("confirm_password", "").strip()

    if password != confirm_password:
        flash("Password and confirm password must match.", "error")
        return redirect(url_for("admin_dashboard"))

    hashed = generate_password_hash(password)

    db = get_db()
    db.execute(
        "INSERT INTO patrons (name, email, phone, password) VALUES (?, ?, ?, ?)",
        (name, email, phone, hashed)
    )
    db.commit()

    flash("Patron added successfully.", "success")
    return redirect(url_for("admin_dashboard"))

@app.post("/admin/scan-checkout")
def admin_scan_checkout():
    if not _dev_role_ok("admin"):
        flash("Admin role required.", "error")
        return redirect(url_for("login"))

    patron_name = request.form.get("patron_name", "").strip()
    book_id = request.form.get("book_id", "").strip()

    if not patron_name or not book_id:
        flash("Patron name and book ID are required.", "error")
        return redirect(url_for("admin_dashboard"))

    db = get_db()

    patron = db.execute(
        "SELECT id FROM patrons WHERE name = ?", (patron_name,)
    ).fetchone()
    if not patron:
        flash("Patron not found.", "error")
        return redirect(url_for("admin_dashboard"))

    book = db.execute(
        "SELECT id FROM books WHERE id = ?", (book_id,)
    ).fetchone()
    if not book:
        flash("Book not found.", "error")
        return redirect(url_for("admin_dashboard"))

    db.execute(
        "INSERT INTO checkouts (book_id, patron_id, due_date, returned) "
        "VALUES (?, ?, date('now','+14 days'), 0)",
        (book_id, patron["id"])
    )
    db.execute(
        "UPDATE books SET status='checked_out' WHERE id = ?", (book_id,)
    )
    db.commit()

    flash("Book checked out successfully.", "success")
    return redirect(url_for("admin_dashboard"))

@app.post("/admin/scan-checkin")
def admin_scan_checkin():
    if not _dev_role_ok("admin"):
        flash("Admin role required.", "error")
        return redirect(url_for("login"))

    book_id = request.form.get("book_id", "").strip()

    if not book_id:
        flash("Book ID is required.", "error")
        return redirect(url_for("admin_dashboard"))

    db = get_db()
    db.execute(
        "UPDATE checkouts SET returned=1 WHERE book_id = ? AND returned = 0",
        (book_id,)
    )
    db.execute(
        "UPDATE books SET status='in_stock' WHERE id = ?", (book_id,)
    )
    db.commit()

    flash("Book checked in successfully.", "success")
    return redirect(url_for("admin_dashboard"))

# ------------------------------
# CUSTOMER ROUTES
# ------------------------------

@app.get("/customer")
def customer_home():
    if not _dev_role_ok("customer"):
        flash("Customer role required.", "error")
        return redirect(url_for("login"))

    db = get_db()

    books = db.execute(
        "SELECT id, title, author, genre, status FROM books ORDER BY id"
    ).fetchall()

    patron_id = session.get("patron_id")
    my_books = []

    if patron_id:
        my_books = db.execute(
            """
            SELECT books.title, books.status, checkouts.due_date, books.id AS book_id
            FROM checkouts
            JOIN books ON books.id = checkouts.book_id
            WHERE checkouts.patron_id = ?
              AND checkouts.returned = 0
            """,
            (patron_id,)
        ).fetchall()

    return render_template("patron_placeholder.html", books=books, my_books=my_books)

@app.post("/books/reserve/<int:book_id>")
def reserve_book(book_id):
    if not _dev_role_ok("customer"):
        flash("Customer role required.", "error")
        return redirect(url_for("login"))

    patron_id = session.get("patron_id")
    if not patron_id:
        flash("No patron session found.", "error")
        return redirect(url_for("login"))

    db = get_db()
    db.execute(
        "INSERT INTO checkouts (book_id, patron_id, due_date, returned) "
        "VALUES (?, ?, date('now','+14 days'), 0)",
        (book_id, patron_id)
    )
    db.execute(
        "UPDATE books SET status='checked_out' WHERE id = ?", (book_id,)
    )
    db.commit()

    flash("Book reserved successfully.", "success")
    return redirect(url_for("customer_home"))

@app.post("/books/cancel/<int:book_id>")
def cancel_book(book_id):
    if not _dev_role_ok("customer"):
        flash("Customer role required.", "error")
        return redirect(url_for("login"))

    patron_id = session.get("patron_id")
    if not patron_id:
        flash("No patron session found.", "error")
        return redirect(url_for("login"))

    db = get_db()
    db.execute(
        "UPDATE checkouts SET returned=1 "
        "WHERE book_id = ? AND patron_id = ? AND returned = 0",
        (book_id, patron_id)
    )
    db.execute(
        "UPDATE books SET status='in_stock' WHERE id = ?", (book_id,)
    )
    db.commit()

    flash("Book returned successfully.", "success")
    return redirect(url_for("customer_home"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)
