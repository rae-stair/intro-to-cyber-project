import os
import re
import sqlite3
import datetime
from flask import Flask, flash, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash

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

MAX_FAILED_ATTEMPTS = 5
COOLDOWN_SECONDS = 120

def get_attempts(ip):
    db = get_db()
    row = db.execute("SELECT attempts, last_attempt FROM login_attempts WHERE ip = ?", (ip,)).fetchone()
    if row:
        return row["attempts"], row["last_attempt"]
    return 0, None

def parse_sqlite_timestamp(ts):
    if not ts:
        return None
    try:
        return datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S.%f")
    except:
        return datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")

def increment_attempts(ip):
    db = get_db()
    row = db.execute("SELECT attempts FROM login_attempts WHERE ip = ?", (ip,)).fetchone()
    if row:
        db.execute("UPDATE login_attempts SET attempts = attempts + 1, last_attempt = CURRENT_TIMESTAMP WHERE ip = ?", (ip,))
    else:
        db.execute("INSERT INTO login_attempts (ip, attempts, last_attempt) VALUES (?, 1, CURRENT_TIMESTAMP)", (ip,))
    db.commit()

def reset_attempts(ip):
    db = get_db()
    db.execute("DELETE FROM login_attempts WHERE ip = ?", (ip,))
    db.commit()

def is_cooldown_over(last_attempt):
    if not last_attempt:
        return True
    last = parse_sqlite_timestamp(last_attempt)
    now = datetime.datetime.utcnow()
    return (now - last).total_seconds() >= COOLDOWN_SECONDS

DEV_ROLES = {"admin", "customer"}

def _dev_skip_login_enabled():
    return True

def _session_has_auth():
    return bool(session.get("dev_skip_auth"))

def _dev_role_ok(role):
    return _session_has_auth() and session.get("dev_role") == role

def _validate_new_patron_password(password):
    if len(password) < 12:
        return "Password must be at least 12 characters long."
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter."
    if not re.search(r"[0-9]", password):
        return "Password must contain at least one number."
    if not re.search(r"[^A-Za-z0-9]", password):
        return "Password must contain at least one symbol."
    return None

app = Flask(__name__, template_folder="html", static_folder="static")
app.secret_key = "supersecretdevkey123"

@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


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
    session.pop("patron_id", None)
    return redirect(url_for("admin_dashboard"))

@app.get("/dev/logout")
def dev_logout():
    session.clear()
    return redirect(url_for("login"))

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

    if not username or not password:
        increment_attempts(ip)
        flash("Username and password are required.", "error")
        return redirect(url_for("login"))

    failed_attempts, last_attempt = get_attempts(ip)

    if failed_attempts >= MAX_FAILED_ATTEMPTS:
        if is_cooldown_over(last_attempt):
            reset_attempts(ip)
        else:
            last = parse_sqlite_timestamp(last_attempt)
            now = datetime.datetime.utcnow()
            elapsed = int((now - last).total_seconds())
            remaining = COOLDOWN_SECONDS - elapsed
            if remaining < 0:
                remaining = 0
            flash(f"Too many failed attempts. Try again in {remaining} seconds.", "error")
            return redirect(url_for("login"))

    db = get_db()

    admin = db.execute("SELECT id, name, password FROM admins WHERE name = ?", (username,)).fetchone()
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

    patron = db.execute("SELECT id, name, email, password FROM patrons WHERE name = ? OR email = ?", (username, username)).fetchone()
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

    increment_attempts(ip)
    flash("No matching account found.", "error")
    return redirect(url_for("login"))

@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.get("/_pf/css/<path:filename>")
def project_front_css(filename):
    return send_from_directory(PROJECT_FRONT_CSS, filename)

@app.get("/_pf/js/<path:filename>")
def project_front_js(filename):
    return send_from_directory(PROJECT_FRONT_JS, filename)

def load_admin_dashboard_data():
    db = get_db()

    overdue = db.execute("""
        SELECT patrons.name, patrons.phone, books.title, books.id AS book_id,
               checkouts.due_date,
               CAST((julianday('now') - julianday(checkouts.due_date)) AS INT) AS days_overdue
        FROM checkouts
        JOIN patrons ON patrons.id = checkouts.patron_id
        JOIN books ON books.id = checkouts.book_id
        WHERE checkouts.returned = 0
          AND checkouts.due_date < date('now')
        ORDER BY days_overdue DESC
    """).fetchall()

    patrons_raw = db.execute("SELECT id, name, email, phone FROM patrons ORDER BY id").fetchall()

    patrons = []
    for p in patrons_raw:
        books_out = db.execute("""
            SELECT books.title, books.status
            FROM checkouts
            JOIN books ON books.id = checkouts.book_id
            WHERE checkouts.patron_id = ?
              AND checkouts.returned = 0
        """, (p["id"],)).fetchall()
        patrons.append({
            "id": p["id"],
            "name": p["name"],
            "email": p["email"],
            "phone": p["phone"],
            "books": books_out
        })

    total_books = db.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    total_patrons = db.execute("SELECT COUNT(*) FROM patrons").fetchone()[0]
    checked_out = db.execute("SELECT COUNT(*) FROM books WHERE status='checked_out'").fetchone()[0]

    return overdue, patrons, total_books, total_patrons, checked_out

@app.get("/admin")
def admin_dashboard():
    if not _dev_role_ok("admin"):
        flash("Admin role required.", "error")
        return redirect(url_for("login"))

    overdue, patrons, total_books, total_patrons, checked_out = load_admin_dashboard_data()

    return render_template(
        "admin.html",
        overdue=overdue,
        patrons=patrons,
        total_books=total_books,
        total_patrons=total_patrons,
        checked_out=checked_out,
        checkout_error=None
    ), 200, {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0"
    }

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

    if len(name) > 50:
        flash("Name too long.", "error")
        return redirect(url_for("admin_dashboard"))

    if len(email) > 100:
        flash("Email too long.", "error")
        return redirect(url_for("admin_dashboard"))

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        flash("Invalid email format.", "error")
        return redirect(url_for("admin_dashboard"))

    if not phone.isdigit() or len(phone) < 7:
        flash("Invalid phone number.", "error")
        return redirect(url_for("admin_dashboard"))

    password_error = _validate_new_patron_password(password)
    if password_error:
        flash(password_error, "error")
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

# ⭐ THIS IS THE ONLY ROUTE MODIFIED — FLASH REMOVED, INLINE ERROR ADDED
@app.post("/admin/scan-checkout")
def admin_scan_checkout():
    if not _dev_role_ok("admin"):
        return redirect(url_for("login"))

    patron_id = request.form.get("patron_id", "").strip()
    book_id = request.form.get("book_id", "").strip()

    checkout_error = None
    db = get_db()

    if not patron_id or not book_id:
        checkout_error = "Patron ID and book ID are required."
    else:
        patron = db.execute("SELECT id FROM patrons WHERE id = ?", (patron_id,)).fetchone()
        if not patron:
            checkout_error = "Patron not found."
        else:
            book = db.execute("SELECT id, status FROM books WHERE id = ?", (book_id,)).fetchone()
            if not book:
                checkout_error = "Book not found."
            elif book["status"] != "in_stock":
                checkout_error = "Book unavailable."
            else:
                active_checkout = db.execute(
                    "SELECT id FROM checkouts WHERE book_id = ? AND returned = 0",
                    (book_id,)
                ).fetchone()
                if active_checkout:
                    checkout_error = "Book unavailable."

    if checkout_error:
        overdue, patrons, total_books, total_patrons, checked_out = load_admin_dashboard_data()
        return render_template(
            "admin.html",
            overdue=overdue,
            patrons=patrons,
            total_books=total_books,
            total_patrons=total_patrons,
            checked_out=checked_out,
            checkout_error=checkout_error
        )

    db.execute(
        "INSERT INTO checkouts (book_id, patron_id, due_date, returned) VALUES (?, ?, date('now','+14 days'), 0)",
        (book_id, patron_id)
    )
    db.execute("UPDATE books SET status='checked_out' WHERE id = ?", (book_id,))
    db.commit()

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
    db.execute("UPDATE checkouts SET returned=1 WHERE book_id = ? AND returned = 0", (book_id,))
    db.execute("UPDATE books SET status='in_stock' WHERE id = ?", (book_id,))
    db.commit()

    flash("Book checked in successfully.", "success")
    return redirect(url_for("admin_dashboard"))

@app.get("/customer")
def customer_home():
    if not _dev_role_ok("customer"):
        flash("Customer role required.", "error")
        return redirect(url_for("login"))

    db = get_db()

    books = db.execute("SELECT id, title, author, genre, status FROM books ORDER BY id").fetchall()

    patron_id = session.get("patron_id")
    my_books = []

    if patron_id:
        my_books = db.execute("""
            SELECT books.title, books.status, checkouts.due_date, books.id AS book_id
            FROM checkouts
            JOIN books ON books.id = checkouts.book_id
            WHERE checkouts.patron_id = ?
              AND checkouts.returned = 0
        """, (patron_id,)).fetchall()

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
        "INSERT INTO checkouts (book_id, patron_id, due_date, returned) VALUES (?, ?, date('now','+14 days'), 0)",
        (book_id, patron_id)
    )
    db.execute("UPDATE books SET status='checked_out' WHERE id = ?", (book_id,))
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
        "UPDATE checkouts SET returned=1 WHERE book_id = ? AND patron_id = ? AND returned = 0",
        (book_id, patron_id)
    )
    db.execute("UPDATE books SET status='in_stock' WHERE id = ?", (book_id,))
    db.commit()

    flash("Book returned successfully.", "success")
    return redirect(url_for("customer_home"))




if __name__ == "__main__":
    app.run(debug=True, port=5000)
