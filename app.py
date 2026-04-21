from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "chipotlechicken" # Key to prevent session tampering/forging

# Temp database before SQL database is set up

users = [
    {"id": 1, "username": "test1", "password": generate_password_hash("mypassword123"), "clearance": "admin"},
    {"id": 2, "username": "test2", "password": generate_password_hash("password123"), "clearance": "customer"},
    {"id": 3, "username": "test3", "password": generate_password_hash("12345"), "clearance": "staff"},
]

bookList = [
    {"id": 1, "title": "We want chicken", "author": "Me", "available": True, "reserved_by": None},
    {"id": 2, "title": "Chicken chicken chicken", "author": "Me again", "available": True, "reserved_by": None},
    {"id": 3, "title": "CHICKEN!", "author": "ME", "available": False, "reserved_by": 3},
]

# Routes for user registration and login
@app.route("/")
def home():
    return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
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
            return redirect("/login")
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

    # Adding a new user to the database
        new_user = {
            "id": len(users) + 1,
            "username": username,
            "password": generate_password_hash(password),
            "clearance": "customer"
        }
        users.append(new_user)
        flash("Registration successful. Please log in.")
        return redirect("/login")
    return render_template("register.html")

# Admin dashboard
@app.route("/admin")
def admin_dashboard():
    if "user_id" not in session:
        flash("Please login to access the administrator dashboard.")
        return redirect("/login")
    user = next((u for u in users if u["id"] == session["user_id"]), None)
    if user and user["clearance"] == "admin":
        return render_template("admin.html")
    else:
        flash("You do not have the permissions to access the administrator dashbooard.")
        return redirect("/login")
    
# Books page route for customers
@app.route("/books")
def books():
    if "user_id" not in session:
        flash("Please login to access our library!")
        return redirect("/login")
    user = next((u for u in users if u["id"] == session["user_id"]), None)
    if user and user["clearance"] == "customer":
        return render_template("books.html")

@app.route("/books/reserve/<int:book_id>", methods=["POST"])
def reserve(book_id):
    if "user_id" not in session:
        flash("Please login to access our library!")
        return redirect("/login")
    
    book = next((b for b in bookList if b["id"] == book_id), None)
    if book:
        if  book["id"] == book_id and book["available"]:
            book["available"] = False
            book["reserved_by"] = session["user_id"]
            flash(f"You successfully reserved '{book['title']}' by {book['author']}.")
        else:
            flash(f"Unfortunately '{book['title']}' is already checked out or reserved.")
    return redirect("/books")

# Logging out clears the session and redirects to the home page
@app.route("/logout")
def logout():
    session.clear()
    flash("You have successfully been logged out.")
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)

