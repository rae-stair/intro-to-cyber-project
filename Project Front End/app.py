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
    request,
    send_from_directory,
    session,
    url_for,
)

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_FRONT_DIR = os.path.join(ROOT_DIR, "html")
PROJECT_FRONT_CSS = os.path.join(ROOT_DIR, "static", "css")
PROJECT_FRONT_JS = os.path.join(ROOT_DIR, "static", "js")

# Only admin + customer exist now
DEV_ROLES = frozenset({"admin", "customer"})

app = Flask(__name__, template_folder='html', static_folder='static')
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-in-production")


def _dev_skip_login_enabled() -> bool:
    """TEMPORARY: allow bypassing login only in debug or when explicitly opted in."""
    if os.environ.get("ALLOW_DEV_LOGIN_SKIP", "").lower() in ("1", "true", "yes"):
        return True
    return bool(current_app.debug)


def _session_has_auth() -> bool:
    """TEMPORARY: dev skip flag; later add Firebase/session checks."""
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
    # Stub: no SQL/Firebase yet — keep form UX without validating credentials.
    flash(
        "Sign-in is not active yet. Database and authentication are still being connected.",
        "info",
    )
    return redirect(url_for("login"))


@app.get("/_pf/css/<path:filename>")
def project_front_css(filename):
    """Static assets for Project Front End/admin.html when served from /admin."""
    return send_from_directory(PROJECT_FRONT_CSS, filename)


@app.get("/_pf/js/<path:filename>")
def project_front_js(filename):
    return send_from_directory(PROJECT_FRONT_JS, filename)


@app.get("/dev/skip-login")
def dev_skip_login():
    """TEMPORARY — remove before production. ?role=admin|customer"""
    if not _dev_skip_login_enabled():
        abort(404)

    role = (request.args.get("role") or "admin").strip().lower()

    if role not in DEV_ROLES:
        flash("Invalid dev role. Choose admin or customer.", "error")
        return redirect(url_for("login"))

    session["dev_skip_auth"] = True
    session["dev_role"] = role

    flash(
        f"Temporary dev mode: signed in as {role}. Remove dev bypass before production.",
        "warning",
    )

    # Staff no longer exists — only admin or customer
    if role == "admin":
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("customer_home"))


@app.get("/dev/logout")
def dev_logout():
    """TEMPORARY — clear dev session."""
    session.pop("dev_skip_auth", None)
    session.pop("dev_role", None)
    flash("Dev session cleared.", "info")
    return redirect(url_for("login"))


@app.get("/admin")
def admin_dashboard():
    """Admin UI (Project Front End/admin.html). TEMP: requires dev_role admin."""
    if not _dev_role_ok("admin"):
        flash("This page requires the admin role. Use dev bypass → Admin.", "error")
        return redirect(url_for("login"))
    return send_from_directory(PROJECT_FRONT_DIR, "admin.html")


@app.get("/customer")
def customer_home():
    """patron placeholder until patron UI is integrated."""
    if not _dev_role_ok("customer"):
        flash(
            "This page requires the customer role. Use dev bypass → Customer.",
            "error",
        )
        return redirect(url_for("login"))
    return render_template("patron_placeholder.html")


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
