"""Business logic. EVERY function that changes data runs inside `with LOCK:`
(the critical section), so only one thread can modify the library data at a time."""
import threading
import time
from datetime import date, datetime, timedelta

import storage as store

LOCK = threading.Lock()  # the mutex
LOAN_DAYS = 14
FINE_PER_DAY = 5
MAX_ACTIVE_ISSUES = 5


def _ts():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def _r(ok, msg, **extra):
    return {"ok": ok, "message": msg, **extra}


def find(items, key, value):
    return next((i for i in items if i[key] == value), None)


def _next_id(prefix, items, key, width):
    nums = [int(i[key].split("-")[-1]) for i in items] or [0]
    return f"{prefix}-{max(nums) + 1:0{width}d}"


def _release_copy(copy, resv):
    """A copy became free: give it to the first waiting reservation, else mark Available."""
    nxt = next((r for r in resv if r["book_id"] == copy["book_id"] and r["status"] == "Pending"), None)
    if nxt:
        copy["status"] = "Reserved"
        nxt["status"] = "Ready"
        nxt["copy_id"] = copy["copy_id"]
        nxt["ready_date"] = date.today().isoformat()
        return nxt
    copy["status"] = "Available"
    return None


# ---------------------------------------------------------------- ISSUE (critical section)
def issue_book(student_id, book_id, delay=0.0, who=None):
    who = who or threading.current_thread().name
    log = [f"[{_ts()}] {who}: requesting mutex lock..."]
    with LOCK:  # ---- ENTER CRITICAL SECTION
        log.append(f"[{_ts()}] {who}: LOCK ACQUIRED -> inside critical section")
        ok, msg, txn = _issue_locked(student_id, book_id, delay, log, who)
        log.append(f"[{_ts()}] {who}: leaving critical section -> LOCK RELEASED")
    # ---- EXIT CRITICAL SECTION
    return _r(ok, msg, txn=txn, log=log)


def _issue_locked(student_id, book_id, delay, log, who):
    students, books = store.load("students"), store.load("books")
    copies, txns, resv = store.load("copies"), store.load("transactions"), store.load("reservations")
    student, book = find(students, "student_id", student_id), find(books, "book_id", book_id)
    if not student:
        return False, "Invalid student ID.", None
    if not book:
        return False, "Invalid book ID.", None
    active = [t for t in txns if t["student_id"] == student_id and t["status"] == "Issued"]
    if len(active) >= MAX_ACTIVE_ISSUES:
        return False, f"{student['name']} has reached the limit of {MAX_ACTIVE_ISSUES} issued books.", None
    if any(t["book_id"] == book_id for t in active):
        return False, f"{student['name']} already holds a copy of this book.", None

    log.append(f"[{_ts()}] {who}: checking availability of '{book['title']}'")
    ready = next((r for r in resv if r["student_id"] == student_id and r["book_id"] == book_id
                  and r["status"] == "Ready"), None)
    if ready:
        copy = find(copies, "copy_id", ready["copy_id"])
    else:
        copy = next((c for c in copies if c["book_id"] == book_id and c["status"] == "Available"), None)
    if copy is None:
        log.append(f"[{_ts()}] {who}: no copy available -> request REJECTED")
        return False, f"No copy of '{book['title']}' is available right now. You can reserve it.", None
    if any(t["copy_id"] == copy["copy_id"] and t["status"] == "Issued" for t in txns):
        return False, "This physical copy is already actively issued.", None

    log.append(f"[{_ts()}] {who}: found {copy['copy_id']}")
    if delay:
        time.sleep(delay)  # simulates slow work; without the mutex a race would happen here
    copy["status"] = "Issued"
    today = date.today()
    txn = {"txn_id": _next_id("TXN", txns, "txn_id", 5), "student_id": student_id, "book_id": book_id,
           "copy_id": copy["copy_id"], "issue_date": today.isoformat(),
           "due_date": (today + timedelta(days=LOAN_DAYS)).isoformat(),
           "return_date": None, "status": "Issued", "fine": 0}
    txns.append(txn)
    if ready:
        ready["status"] = "Fulfilled"
        store.save("reservations", resv)
    store.save("copies", copies)
    store.save("transactions", txns)
    log.append(f"[{_ts()}] {who}: {copy['copy_id']} marked ISSUED ({txn['txn_id']})")
    return True, (f"{txn['txn_id']}: '{book['title']}' ({copy['copy_id']}) issued to {student['name']}. "
                  f"Due on {txn['due_date']}."), txn


# ---------------------------------------------------------------- RETURN
def return_book(txn_id):
    with LOCK:
        txns, copies, resv = store.load("transactions"), store.load("copies"), store.load("reservations")
        t = next((x for x in txns if x["txn_id"] == txn_id and x["status"] == "Issued"), None)
        if not t:
            return _r(False, "Active transaction not found.")
        copy = find(copies, "copy_id", t["copy_id"])
        late = max(0, (date.today() - date.fromisoformat(t["due_date"])).days)
        t.update(return_date=date.today().isoformat(), status="Returned", fine=late * FINE_PER_DAY)
        nxt = _release_copy(copy, resv) if copy else None
        store.save("transactions", txns)
        store.save("copies", copies)
        store.save("reservations", resv)
    msg = f"{txn_id} returned. "
    msg += f"Late by {late} day(s): fine ₹{t['fine']}. " if late else "Returned on time, no fine. "
    if nxt:
        msg += "The copy is now reserved for the next student in the queue."
    return _r(True, msg)


# ---------------------------------------------------------------- RESERVATIONS
def reserve_book(student_id, book_id):
    with LOCK:
        students, books = store.load("students"), store.load("books")
        copies, txns, resv = store.load("copies"), store.load("transactions"), store.load("reservations")
        student, book = find(students, "student_id", student_id), find(books, "book_id", book_id)
        if not student or not book:
            return _r(False, "Invalid student or book.")
        if any(c["book_id"] == book_id and c["status"] == "Available" for c in copies):
            return _r(False, "Copies are available right now, so please issue the book instead.")
        if any(t["student_id"] == student_id and t["book_id"] == book_id and t["status"] == "Issued" for t in txns):
            return _r(False, "This student already has the book issued.")
        if any(r["student_id"] == student_id and r["book_id"] == book_id and r["status"] in ("Pending", "Ready")
               for r in resv):
            return _r(False, "This student already has an open reservation for this book.")
        res = {"res_id": _next_id("RES", resv, "res_id", 4), "student_id": student_id, "book_id": book_id,
               "date": date.today().isoformat(), "status": "Pending", "copy_id": None}
        resv.append(res)
        store.save("reservations", resv)
        pos = sum(1 for r in resv if r["book_id"] == book_id and r["status"] in ("Pending", "Ready"))
    return _r(True, f"{res['res_id']} created. {student['name']} is #{pos} in the queue for '{book['title']}'.")


def cancel_reservation(res_id):
    with LOCK:
        resv, copies = store.load("reservations"), store.load("copies")
        r = find(resv, "res_id", res_id)
        if not r or r["status"] not in ("Pending", "Ready"):
            return _r(False, "Open reservation not found.")
        was_ready = r["status"] == "Ready"
        r["status"] = "Cancelled"
        if was_ready:
            copy = find(copies, "copy_id", r["copy_id"])
            if copy:
                _release_copy(copy, resv)
        store.save("reservations", resv)
        store.save("copies", copies)
    return _r(True, f"{res_id} cancelled.")


# ---------------------------------------------------------------- COPY CONTROL
def set_copy_disabled(copy_id, disable):
    with LOCK:
        copies, resv = store.load("copies"), store.load("reservations")
        c = find(copies, "copy_id", copy_id)
        if not c:
            return _r(False, "Copy not found.")
        if disable and c["status"] != "Available":
            return _r(False, "Only an Available copy can be disabled.")
        if not disable and c["status"] != "Disabled":
            return _r(False, "This copy is not disabled.")
        if disable:
            c["status"] = "Disabled"
        else:
            _release_copy(c, resv)
        store.save("copies", copies)
        store.save("reservations", resv)
    return _r(True, f"{copy_id} {'disabled' if disable else 'enabled'}.")


# ---------------------------------------------------------------- BOOKS
def add_book(isbn, title, author, category, publisher, total, shelf):
    with LOCK:
        books, copies = store.load("books"), store.load("copies")
        if not title.strip() or not author.strip():
            return _r(False, "Title and author are required.")
        if total < 1:
            return _r(False, "A book needs at least 1 copy.")
        if isbn.strip() and any(b["isbn"] == isbn.strip() for b in books):
            return _r(False, "A book with this ISBN already exists.")
        bid = _next_id("BOOK", books, "book_id", 3)
        books.append({"book_id": bid, "isbn": isbn.strip(), "title": title.strip(), "author": author.strip(),
                      "category": category.strip() or "General", "publisher": publisher.strip(),
                      "total_copies": int(total), "shelf": shelf.strip()})
        for k in range(1, int(total) + 1):
            copies.append({"copy_id": f"{bid}-COPY-{k:02d}", "book_id": bid, "status": "Available"})
        store.save("books", books)
        store.save("copies", copies)
    return _r(True, f"{bid} added with {int(total)} physical copies.")


def update_book(book_id, isbn, title, author, category, publisher, total, shelf):
    with LOCK:
        books, copies, resv = store.load("books"), store.load("copies"), store.load("reservations")
        b = find(books, "book_id", book_id)
        if not b:
            return _r(False, "Book not found.")
        if not title.strip() or not author.strip() or total < 1:
            return _r(False, "Title, author and at least 1 copy are required.")
        if isbn.strip() and any(x["isbn"] == isbn.strip() and x["book_id"] != book_id for x in books):
            return _r(False, "Another book already uses this ISBN.")
        mine = [c for c in copies if c["book_id"] == book_id]
        total = int(total)
        if total > len(mine):
            top = max(int(c["copy_id"].rsplit("-", 1)[1]) for c in mine) if mine else 0
            for k in range(top + 1, top + 1 + total - len(mine)):
                c = {"copy_id": f"{book_id}-COPY-{k:02d}", "book_id": book_id, "status": "Available"}
                copies.append(c)
                _release_copy(c, resv)
        elif total < len(mine):
            need = len(mine) - total
            removable = [c for c in reversed(mine) if c["status"] in ("Available", "Disabled")]
            if len(removable) < need:
                return _r(False, "Cannot remove copies that are issued or reserved.")
            gone = {c["copy_id"] for c in removable[:need]}
            copies = [c for c in copies if c["copy_id"] not in gone]
        b.update(isbn=isbn.strip(), title=title.strip(), author=author.strip(), category=category.strip(),
                 publisher=publisher.strip(), total_copies=total, shelf=shelf.strip())
        store.save("books", books)
        store.save("copies", copies)
        store.save("reservations", resv)
    return _r(True, f"{book_id} updated.")


def delete_book(book_id):
    with LOCK:
        books, copies, resv = store.load("books"), store.load("copies"), store.load("reservations")
        if not find(books, "book_id", book_id):
            return _r(False, "Book not found.")
        if any(c["book_id"] == book_id and c["status"] in ("Issued", "Reserved") for c in copies):
            return _r(False, "Cannot delete: some copies are issued or reserved.")
        if any(r["book_id"] == book_id and r["status"] in ("Pending", "Ready") for r in resv):
            return _r(False, "Cannot delete: the book has open reservations.")
        store.save("books", [b for b in books if b["book_id"] != book_id])
        store.save("copies", [c for c in copies if c["book_id"] != book_id])
    return _r(True, f"{book_id} deleted (transaction history is kept).")


# ---------------------------------------------------------------- STUDENTS
def _check_student(name, email, phone):
    if not name.strip():
        return "Student name is required."
    if "@" not in email or "." not in email:
        return "Enter a valid email address."
    if not (phone.strip().isdigit() and len(phone.strip()) == 10):
        return "Phone number must be exactly 10 digits."
    return None


def register_student(name, department, email, phone):
    with LOCK:
        students = store.load("students")
        err = _check_student(name, email, phone)
        if err:
            return _r(False, err)
        if any(s["email"].lower() == email.strip().lower() for s in students):
            return _r(False, "A student with this email already exists.")
        sid = _next_id("STU", students, "student_id", 3)
        students.append({"student_id": sid, "name": name.strip(), "department": department.strip(),
                         "email": email.strip(), "phone": phone.strip(), "registered": date.today().isoformat()})
        store.save("students", students)
    return _r(True, f"{sid} registered: {name.strip()}.")


def update_student(student_id, name, department, email, phone):
    with LOCK:
        students = store.load("students")
        s = find(students, "student_id", student_id)
        err = _check_student(name, email, phone)
        if not s:
            return _r(False, "Student not found.")
        if err:
            return _r(False, err)
        s.update(name=name.strip(), department=department.strip(), email=email.strip(), phone=phone.strip())
        store.save("students", students)
    return _r(True, f"{student_id} updated.")


def delete_student(student_id):
    with LOCK:
        students, txns, resv = store.load("students"), store.load("transactions"), store.load("reservations")
        if not find(students, "student_id", student_id):
            return _r(False, "Student not found.")
        if any(t["student_id"] == student_id and t["status"] == "Issued" for t in txns):
            return _r(False, "Cannot delete: the student still has issued books.")
        if any(r["student_id"] == student_id and r["status"] in ("Pending", "Ready") for r in resv):
            return _r(False, "Cannot delete: the student has open reservations.")
        store.save("students", [s for s in students if s["student_id"] != student_id])
    return _r(True, f"{student_id} deleted (history is kept).")