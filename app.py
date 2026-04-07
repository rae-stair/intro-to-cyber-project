"""
Library database system — Flask entry (CSC 2362).
Login UI is served here; real authentication will use SQL/Firebase later.
"""

import os

from flask import (
    Flask,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    send_from_directory,
    session,
    url_for,
)

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-in-production")


def _dev_skip_login_enabled() -> bool:
    """TEMPORARY: allow bypassing login only in debug or when explicitly opted in."""
    if os.environ.get("ALLOW_DEV_LOGIN_SKIP", "").lower() in ("1", "true", "yes"):
        return True
    return bool(current_app.debug)


def _session_has_auth() -> bool:
    """TEMPORARY: dev skip flag; later add Firebase/session checks."""
    return bool(session.get("dev_skip_auth"))


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
    # Stub: no SQL/Firebase yet — keep form UX without validating credentials.
    flash(
        "Sign-in is not active yet. Database and authentication are still being connected.",
        "info",
    )
    return redirect(url_for("login"))


@app.get("/dev/skip-login")
def dev_skip_login():
    """TEMPORARY — remove before production. Navigates to staff dashboard without real auth."""
    if not _dev_skip_login_enabled():
        abort(404)
    session["dev_skip_auth"] = True
    flash(
        "Temporary dev mode: login was skipped. Remove /dev/skip-login before production.",
        "warning",
    )
    return redirect(url_for("staff_dashboard"))


@app.get("/staff")
def staff_dashboard():
    """Staff UI prototype (books.html) — requires session until Firebase handles auth."""
    if not _session_has_auth():
        return redirect(url_for("login"))
    return send_from_directory(ROOT_DIR, "books.html")


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
