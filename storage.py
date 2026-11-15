"""JSON file storage. Each 'table' is one JSON file inside the data/ folder."""
import json
import os
from datetime import date, timedelta

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
NAMES = ["books", "copies", "students", "transactions", "reservations"]


def _path(name):
    return os.path.join(DATA_DIR, f"{name}.json")


def load(name):
    try:
        with open(_path(name), "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save(name, data):
    """Write to a temp file first, then swap it in, so a file is never half-written."""
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = _path(name) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _path(name))


def init_storage():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(_path("books")):
        _seed()
    for n in NAMES:
        if not os.path.exists(_path(n)):
            save(n, [])


def _seed():
    today = date.today()
    spec = [
        ("978-0262033848", "Introduction to Algorithms", "Thomas H. Cormen", "Computer Science", "MIT Press", "A-01", 3),
        ("978-1119800363", "Operating System Concepts", "Abraham Silberschatz", "Computer Science", "Wiley", "A-02", 2),
        ("978-0134494166", "Clean Architecture", "Robert C. Martin", "Software Engineering", "Pearson", "B-01", 1),
        ("978-1491912058", "Python Data Science Handbook", "Jake VanderPlas", "Data Science", "O'Reilly", "C-01", 2),
        ("978-0132350884", "Clean Code", "Robert C. Martin", "Software Engineering", "Prentice Hall", "B-02", 2),
        ("978-0134685991", "Effective Java", "Joshua Bloch", "Programming", "Addison-Wesley", "B-03", 1),
    ]
    books, copies = [], []
    for i, (isbn, title, author, cat, pub, shelf, n) in enumerate(spec, 1):
        bid = f"BOOK-{i:03d}"
        books.append({"book_id": bid, "isbn": isbn, "title": title, "author": author, "category": cat,
                      "publisher": pub, "total_copies": n, "shelf": shelf})
        for k in range(1, n + 1):
            copies.append({"copy_id": f"{bid}-COPY-{k:02d}", "book_id": bid, "status": "Available"})

    people = [("Aarav Reddy", "CSE"), ("Diya Sharma", "CSE"), ("Rohan Patel", "IT"),
              ("Sneha Rao", "ECE"), ("Karthik Nair", "AIML"), ("Meera Iyer", "IT")]
    students = []
    for i, (name, dept) in enumerate(people, 1):
        students.append({"student_id": f"STU-{i:03d}", "name": name, "department": dept,
                         "email": f"{name.split()[0].lower()}@college.edu", "phone": f"98765432{i:02d}",
                         "registered": (today - timedelta(days=200 - i * 10)).isoformat()})

    txns = []

    def add(sid, book_no, issue, ret=None):
        bid = f"BOOK-{book_no:03d}"
        txns.append({"txn_id": f"TXN-{len(txns) + 1:05d}", "student_id": sid, "book_id": bid,
                     "copy_id": f"{bid}-COPY-01", "issue_date": issue.isoformat(),
                     "due_date": (issue + timedelta(days=14)).isoformat(),
                     "return_date": ret.isoformat() if ret else None,
                     "status": "Returned" if ret else "Issued", "fine": 0})

    order = [1, 2, 5, 1, 4, 2, 5, 6, 1, 3, 2, 5, 4, 1, 6, 2]
    for i, bn in enumerate(order):
        issue = today - timedelta(days=150 - i * 9)
        add(f"STU-{i % 6 + 1:03d}", bn, issue, issue + timedelta(days=9 + i % 5))
    add("STU-001", 1, today - timedelta(days=3))
    add("STU-002", 2, today - timedelta(days=5))
    add("STU-003", 5, today - timedelta(days=20))  # overdue example

    for c in copies:
        if c["copy_id"] in ("BOOK-001-COPY-01", "BOOK-002-COPY-01", "BOOK-005-COPY-01"):
            c["status"] = "Issued"
        if c["copy_id"] == "BOOK-001-COPY-03":
            c["status"] = "Disabled"

    save("books", books)
    save("copies", copies)
    save("students", students)
    save("transactions", txns)
    save("reservations", [])