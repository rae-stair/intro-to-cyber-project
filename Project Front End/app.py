import os
import re
import sqlite3
from flask import Flask, abort, current_app, flash, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_FRONT_DIR = os.path.join(ROOT_DIR, "html")
PROJECT_FRONT_CSS = os.path.join(ROOT_DIR, "static", "css")
PROJECT_FRONT_JS = os.path.join(ROOT_DIR, "static", "js")
DB_PATH = os.path.join(ROOT_DIR, "db", "library.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

DEV_ROLES = frozenset({"admin", "customer"})
MIN_PASSWORD_LENGTH = 12
COMMON_PASSWORD_BLOCKLIST = frozenset({
    "password",
    "password1",
    "123456",
    "12345678",
    "123456789",
    "qwerty",
    "abc123",
    "letmein",
    "welcome",
    "admin",
    "admin123",
    "iloveyou",
})

app = Flask(__name__, template_folder="html", static_folder="static")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-in-production")

def _dev_skip_login_enabled() -> bool:
    if os.environ.get("ALLOW_DEV_LOGIN_SKIP", "").lower() in ("1", "true", "yes"):
        return True
    return bool(current_app.debug)

def _session_has_auth() -> bool:
    return bool(session.get("dev_skip_auth"))

def _dev_role_ok(role: str) -> bool:
    return _session_has_auth() and session.get("dev_role") == role

def _validate_new_patron_password(password: str) -> str | None:
    normalized = password.strip()
    if len(normalized) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters."

    if normalized.lower() in COMMON_PASSWORD_BLOCKLIST:
        return "Password is too common. Choose a less guessable password."

    if not re.search(r"[A-Z]", normalized):
        return "Password must include at least one uppercase letter."

    if not re.search(r"[a-z]", normalized):
        return "Password must include at least one lowercase letter."

    if not re.search(r"[0-9]", normalized):
        return "Password must include at least one number."

    if not re.search(r"[^A-Za-z0-9]", normalized):
        return "Password must include at least one symbol."

    return None

@app.context_processor
def _inject_dev_skip_flag():
    return {"dev_skip_login_available": _dev_skip_login_enabled()}

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

    if not username or not password:
        flash("Username and password are required.", "error")
        return redirect(url_for("login"))

    ip = request.remote_addr
    now = time.time()

    # remove old attempts (older than 60 seconds)
    login_attempts[ip] = [t for t in login_attempts[ip] if now - t < 60]

    # block if too many attempts
    if len(login_attempts[ip]) >= 5:
        flash("Too many login attempts. Try again later.", "error")
        return redirect(url_for("login"))

    db = get_db()

    admin = db.execute(
        "SELECT id, name, password FROM admins WHERE name = ?",
        (username,)
    ).fetchone()

    if admin:
        if check_password_hash(admin["password"], password):
            session["dev_skip_auth"] = True
            session["dev_role"] = "admin"
            session.pop("patron_id", None)
            flash(f"Welcome back, {admin['name']}!", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Incorrect password for admin account.", "error")
            return redirect(url_for("login"))

    patron = db.execute(
        "SELECT id, name, email, password FROM patrons WHERE name = ? OR email = ?",
        (username, username)
    ).fetchone()

    if patron:
        if check_password_hash(patron["password"], password):
            session["dev_skip_auth"] = True
            session["dev_role"] = "customer"
            session["patron_id"] = patron["id"]
            flash(f"Welcome, {patron['name']}!", "success")
            return redirect(url_for("customer_home"))
        else:
            flash("Incorrect password for patron account.", "error")
            return redirect(url_for("login"))

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

@app.get("/dev/skip-login")
def dev_skip_login():
    if not _dev_skip_login_enabled():
        abort(404)

    role = (request.args.get("role") or "admin").strip().lower()

    if role not in DEV_ROLES:
        flash("Invalid dev role.", "error")
        return redirect(url_for("login"))

    session["dev_skip_auth"] = True
    session["dev_role"] = role

    if role == "customer":
        session["patron_id"] = 1
    else:
        session.pop("patron_id", None)

    flash(f"Dev mode: signed in as {role}.", "warning")

    if role == "admin":
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("customer_home"))

@app.get("/dev/logout")
def dev_logout():
    session.pop("dev_skip_auth", None)
    session.pop("dev_role", None)
    session.pop("patron_id", None)
    flash("Dev session cleared.", "info")
    return redirect(url_for("login"))

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

    db = get_db()
    db.execute(
        "INSERT INTO patrons (name, email, phone, password) VALUES (?, ?, ?, ?)",
        (name, email, phone, password)
    )
    db.commit()

    flash("Patron added successfully.", "success")
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
        "SELECT id FROM patrons WHERE name = ?",
        (patron_name,)
    ).fetchone()

    if not patron:
        flash("Patron not found.", "error")
        return redirect(url_for("admin_dashboard"))

    book = db.execute(
        "SELECT id FROM books WHERE id = ?",
        (book_id,)
    ).fetchone()

    if not book:
        flash("Book not found.", "error")
        return redirect(url_for("admin_dashboard"))

    db.execute(
        "INSERT INTO checkouts (book_id, patron_id, due_date, returned) VALUES (?, ?, date('now', '+14 days'), 0)",
        (book_id, patron["id"])
    )

    db.execute(
        "UPDATE books SET status = 'checked_out' WHERE id = ?",
        (book_id,)
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
        "UPDATE checkouts SET returned = 1 WHERE book_id = ? AND returned = 0",
        (book_id,)
    )

    db.execute(
        "UPDATE books SET status = 'in_stock' WHERE id = ?",
        (book_id,)
    )

    db.commit()

    flash("Book checked in successfully.", "success")
    return redirect(url_for("admin_dashboard"))

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
    if patron_id is not None:
        my_books = db.execute(
            """
            SELECT books.title,
                   books.status,
                   checkouts.due_date,
                   books.id AS book_id
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
    if patron_id is None:
        flash("No patron session found.", "error")
        return redirect(url_for("login"))

    db = get_db()

    db.execute(
        "INSERT INTO checkouts (book_id, patron_id, due_date, returned) VALUES (?, ?, date('now', '+14 days'), 0)",
        (book_id, patron_id)
    )

    db.execute(
        "UPDATE books SET status = 'checked_out' WHERE id = ?",
        (book_id,)
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
    if patron_id is None:
        flash("No patron session found.", "error")
        return redirect(url_for("login"))

    db = get_db()

    db.execute(
        "UPDATE checkouts SET returned = 1 WHERE book_id = ? AND patron_id = ? AND returned = 0",
        (book_id, patron_id)
    )

    db.execute(
        "UPDATE books SET status = 'in_stock' WHERE id = ?",
        (book_id,)
    )

    db.commit()

    flash("Book returned successfully.", "success")
    return redirect(url_for("customer_home"))

if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
