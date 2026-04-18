import os
import sqlite3
from datetime import datetime, timedelta

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(ROOT_DIR, "db")
DB_PATH = os.path.join(DB_DIR, "library.db")

os.makedirs(DB_DIR, exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# -------------------------
# CREATE TABLES
# -------------------------
cur.executescript("""
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL,          -- genreNumber-bookNumber (e.g., 1-3)
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    genre TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS patrons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT
);

CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    password TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS checkouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    patron_id INTEGER NOT NULL,
    due_date TEXT NOT NULL,
    returned INTEGER DEFAULT 0,
    FOREIGN KEY(book_id) REFERENCES books(id),
    FOREIGN KEY(patron_id) REFERENCES patrons(id)
);
""")

# Clear old data
cur.execute("DELETE FROM books;")
cur.execute("DELETE FROM patrons;")
cur.execute("DELETE FROM admins;")
cur.execute("DELETE FROM checkouts;")

# -------------------------
# INSERT BOOKS (WITH STATUS + CODE)
# genreNumber-bookNumber:
#   1 = Children
#   2 = Classic
#   3 = History
#   4 = Sci-Fi
# -------------------------
cur.executescript("""
INSERT INTO books (id, code, title, author, genre, status) VALUES
(1,  '1-1', 'Charlotte''s Web', 'E. B. White', 'Children', 'in_stock'),
(2,  '1-2', 'Matilda', 'Roald Dahl', 'Children', 'checked_out'),
(3,  '1-3', 'The Tale of Peter Rabbit', 'Beatrix Potter', 'Children', 'in_stock'),
(4,  '1-4', 'Where the Wild Things Are', 'Maurice Sendak', 'Children', 'overdue'),
(5,  '1-5', 'The Cat in the Hat', 'Dr. Seuss', 'Children', 'in_stock'),

(6,  '2-1', 'Pride and Prejudice', 'Jane Austen', 'Classic', 'in_stock'),
(7,  '2-2', '1984', 'George Orwell', 'Classic', 'checked_out'),
(8,  '2-3', 'Moby-Dick', 'Herman Melville', 'Classic', 'overdue'),
(9,  '2-4', 'The Great Gatsby', 'F. Scott Fitzgerald', 'Classic', 'in_stock'),
(10, '2-5', 'To Kill a Mockingbird', 'Harper Lee', 'Classic', 'overdue'),

(11, '3-1', 'The Diary of a Young Girl', 'Anne Frank', 'History', 'in_stock'),
(12, '3-2', 'Team of Rivals', 'Doris Kearns Goodwin', 'History', 'checked_out'),
(13, '3-3', 'The Wright Brothers', 'David McCullough', 'History', 'in_stock'),
(14, '3-4', 'Guns, Germs, and Steel', 'Jared Diamond', 'History', 'in_stock'),
(15, '3-5', 'The Immortal Life of Henrietta Lacks', 'Rebecca Skloot', 'History', 'overdue'),

(16, '4-1', 'Dune', 'Frank Herbert', 'Sci-Fi', 'in_stock'),
(17, '4-2', 'Ender''s Game', 'Orson Scott Card', 'Sci-Fi', 'checked_out'),
(18, '4-3', 'The Hitchhiker''s Guide to the Galaxy', 'Douglas Adams', 'Sci-Fi', 'in_stock'),
(19, '4-4', 'Neuromancer', 'William Gibson', 'Sci-Fi', 'in_stock'),
(20, '4-5', 'Fahrenheit 451', 'Ray Bradbury', 'Sci-Fi', 'overdue');
""")

# -------------------------
# INSERT PATRONS (NO MEMBER IDS)
# -------------------------
cur.executescript("""
INSERT INTO patrons (name, email, phone) VALUES
('John Doe', 'john@example.com', '555-0001'),
('Jane Doe', 'jane@example.com', '555-0002'),
('Jack Doe', 'jack@example.com', '555-0003');
""")

# -------------------------
# INSERT ADMINS
# -------------------------
cur.executescript("""
INSERT INTO admins (name, password) VALUES
('Raegan Stair', 'admin1'),
('Justin McCright', 'admin2'),
('Minseo Lee', 'admin3'),
('Troy Boatner', 'admin4'),
('Christian Gamble', 'admin5');
""")

# -------------------------
# INSERT SAMPLE OVERDUE CHECKOUTS
# -------------------------
today = datetime.now()

sample_overdues = [
    (8, 1, today - timedelta(days=6)),  # Moby-Dick
    (10, 2, today - timedelta(days=8)), # To Kill a Mockingbird
    (9, 3, today - timedelta(days=4)),  # The Great Gatsby
]

for book_id, patron_id, due in sample_overdues:
    cur.execute(
        "INSERT INTO checkouts (book_id, patron_id, due_date, returned) VALUES (?, ?, ?, 0)",
        (book_id, patron_id, due.strftime("%Y-%m-%d"))
    )

conn.commit()
conn.close()

print("Database initialized with status + book codes + overdue data.")
