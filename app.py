"""
Library database system — Flask entry (CSC 2362).
Login UI is served here; real authentication will use SQL/Firebase later.
"""

import os

from flask import Flask, flash, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-in-production")


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


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
