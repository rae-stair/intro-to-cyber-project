import os
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

app = Flask(__name__, template_folder="html", static_folder="static")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-in-production")

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

    db = get_db()

    admin = db.execute(
        "SELECT id, name, password FROM admins WHERE name = ?",
        (username,)
    ).fetchone()

    if admin:
    if check_password_hash(admin["password"], password):
        session.clear()
        session["admin_id"] = admin["id"]
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
            session.clear()
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

@app.get("/admin")
def admin_dashboard():

    if "admin_id" not in session:
        flash("Admin login is required.", "error")
        return redirect(url_for("login"))
    
    db = get_db()

    overdue = db.execute(
        """
        SELECT patrons.name,
               patrons.phone,
               books.id AS book_id,
               books.title,
               checkouts.due_date,
               CAST((julianday('now') - julianday(checkouts.due_date)) AS INT) AS days_overdue
        FROM checkouts
        JOIN patrons ON patrons.id = checkouts.patron_id
        JOIN books ON books.id = checkouts.book_id
        WHERE checkouts.returned = 0
          AND julianday('now') > julianday(checkouts.due_date)
        """
    ).fetchall()

    patrons_raw = db.execute(
        "SELECT id, name, email, phone FROM patrons ORDER BY name"
    ).fetchall()

    patrons = []
    for p in patrons_raw:
        books = db.execute(
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
            "books": books
        })

    total_books = db.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    total_patrons = db.execute("SELECT COUNT(*) FROM patrons").fetchone()[0]
    checked_out = db.execute("SELECT COUNT(*) FROM checkouts WHERE returned = 0").fetchone()[0]

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

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    password = request.form.get("password", "").strip()

    if not name or not email or not phone or not password:
        flash("All fields are required.", "error")
        return redirect(url_for("admin_dashboard"))

    db = get_db()
    db.execute(
        "INSERT INTO patrons (name, email, phone, password) VALUES (?, ?, ?, ?)",
        (name, email, phone, password)
    )
    db.commit()

    flash("Patron added successfully.", "success")
    return redirect(url_for("admin_dashboard"))

@app.post("/admin/scan-checkout")
def admin_scan_checkout():

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

    patron_id = session.get("patron_id")
    if patron_id is None:
        flash("Patron login is required.", "error")
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
