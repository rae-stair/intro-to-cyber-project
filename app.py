from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "chicken" # Key to prevent session tampering/forging

# Temp database before SQL is set up
# Passwords are hashed then stored, new users will automatically be set to 
# default clearance later

users = [
    {"id": 1, "username": "test1", "password": generate_password_hash("mypassword123"), "clearance": "admin"},
    {"id": 2, "username": "test2", "password": generate_password_hash("password123"), "clearance": "default"},
    {"id": 3, "username": "test3", "password": generate_password_hash("12345"), "clearance": "staff"},
]

# Routes for user login
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = next((u for u in users if u["username"] == username), None)
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            if user["clearance"] == "admin":
                return redirect("/admin")
            elif user["clearance"] == "staff":
                return redirect("/staff")
            else:
                return redirect("/books")
        else:
            flash("Invalid username or password.")
            return redirect("/")
    return render_template("login.html")

# Regration route for new users
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if any(u["username"] == username for u in users):
            flash("Username already registered. Please use a different username.")
            return redirect("/register")

    # Add the new user to the database
        new_user = {
            "id": len(users) + 1,
            "username": username,
            "password": generate_password_hash(password),
            "clearance": "default"
        }
        users.append(new_user)
        flash("Registration successful. Please log in.")
        return redirect("/")
    return render_template("register.html")

# Admin dashboard route
@app.route("/admin")
def admin_dashboard():
    if "user_id" not in session:
        flash("Please login to access the administrator dashboard.")
        return redirect("/")
    user = next((u for u in users if u["id"] == session["user_id"]), None)
    if user and user["clearance"] == "admin":
        return render_template("admin.html")
    else:
        flash("You do not have the permissions to access the administrator dashbooard.")
        return redirect("/")



# Staff dashboard route
@app.route("/staff")
def staff_dashboard():
    if "user_id" not in session:
        flash("Please login to access the staff dashboard.")
        return redirect("/")
    user = next((u for u in users if u["id"] == session["user_id"]), None)
    if user and user["clearance"] == "staff":
        return render_template("staff.html")
    else:
        flash("You do not have the permissions to access the staff dashboard.")
        return redirect("/")

# Books page route for customers
@app.route("/books")
def books():
    if "user_id" not in session:
        flash("Please login to access our library!")
        return redirect("/")
    user = next((u for u in users if u["id"] == session["user_id"]), None)
    if user and user["clearance"] == "default":
        return render_template("books.html")

# Logging out clears the session and redirects to the home page
# Unfinished, I need to have access to other screens to finish

@app.route("/logout")
def logout():
    session.clear()
    flash("You have successfully been logged out.")
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)

