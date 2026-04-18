"""
Library database system — Flask entry (CSC 2362).
"""

import os
import sqlite3

from flask import (
    Flask,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

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

app = Flask(__name__, template_folder='html', static_folder='static')
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-in-production")


def _dev_skip_login_enabled() -> bool:
    if os.environ.get("ALLOW_DEV_LOGIN_SKIP", "").lower() in ("1", "true", "yes"):
        return True
    return bool(current_app.debug)


def _session_has_auth() -> bool:
    return bool(session.get("dev_skip_auth"))


def _dev_role_ok(role: str) -> bool:
    return _session_has_auth() and session.get("dev_role") == role


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
    flash("Sign-in is not active yet.", "info")
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

    flash(f"Dev mode: signed in as {role}.", "warning")

    if role == "admin":
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("customer_home"))


@app.get("/dev/logout")
def dev_logout():
    session.pop("dev_skip_auth", None)
    session.pop("dev_role", None)
    flash("Dev session cleared.", "info")
    return redirect(url_for("login"))


@app.get("/admin")
def admin_dashboard():
    if not _dev_role_ok("admin"):
        flash("Admin role required.", "error")
        return redirect(url_for("login"))

    db = get_db()

    overdue = db.execute("""
        SELECT patrons.name,
               patrons.phone,
               books.code AS book_code,
               books.title,
               checkouts.due_date,
               CAST((julianday('now') - julianday(checkouts.due_date)) AS INT) AS days_overdue
        FROM checkouts
        JOIN patrons ON patrons.id = checkouts.patron_id
        JOIN books ON books.id = checkouts.book_id
        WHERE checkouts.returned = 0
          AND julianday('now') > julianday(checkouts.due_date)
    """).fetchall()

    total_books = db.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    total_patrons = db.execute("SELECT COUNT(*) FROM patrons").fetchone()[0]
    checked_out = db.execute("SELECT COUNT(*) FROM checkouts WHERE returned = 0").fetchone()[0]

    return render_template(
        "admin.html",
        overdue=overdue,
        total_books=total_books,
        total_patrons=total_patrons,
        checked_out=checked_out
    )


@app.get("/customer")
def customer_home():
    if not _dev_role_ok("customer"):
        flash("Customer role required.", "error")
        return redirect(url_for("login"))
    return render_template("patron_placeholder.html")


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
