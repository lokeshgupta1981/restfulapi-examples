"""Shared sample data: two users with their own orders, in an SQLite database."""
import sqlite3


def make_db():
    db = sqlite3.connect(":memory:", check_same_thread=False)
    db.executescript("""
        CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, role TEXT, password TEXT);
        CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, item TEXT, total REAL);
        INSERT INTO users VALUES (1, 'alice', 'alice@example.com', 'customer', 'alice-pass');
        INSERT INTO users VALUES (2, 'bob', 'bob@example.com', 'customer', 'bob-pass');
        INSERT INTO users VALUES (3, 'admin', 'admin@example.com', 'admin', 'admin-pass');
        INSERT INTO orders VALUES (101, 1, 'Keyboard', 89.0);
        INSERT INTO orders VALUES (102, 1, 'Mouse', 29.5);
        INSERT INTO orders VALUES (201, 2, 'Monitor', 249.0);
    """)
    return db
