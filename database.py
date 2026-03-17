import sqlite3

conn = sqlite3.connect("booking.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS bookings(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
time TEXT,
amount TEXT,
date TEXT
)
""")

conn.commit()