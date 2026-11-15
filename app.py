"""Library Book Issue & Reservation System (Streamlit dashboard)."""
import threading
from datetime import date, timedelta
from html import escape

import pandas as pd
import plotly.express as px
import streamlit as st

import services as svc
import storage

st.set_page_config(page_title="Library Management System", page_icon="📚", layout="wide")
storage.init_storage()

STATUSES = ["Available", "Issued", "Reserved", "Disabled"]
COLORS = {"Available": "#16a34a", "Issued": "#dc2626", "Reserved": "#f97316", "Disabled": "#6b7280"}
EMOJI = {"Available": "🟢", "Issued": "🔴", "Reserved": "🟠", "Disabled": "⚪"}

CSS = """
<style>
/* ---------- page frame: stop horizontal scrolling, clear the fixed header ---------- */
html, body, .stApp,
[data-testid="stAppViewContainer"], [data-testid="stMain"]{overflow-x:hidden !important;max-width:100vw;}
.stApp{background:#f3f6fb;}
[data-testid="stHeader"]{background:rgba(243,246,251,.92);}
.block-container, [data-testid="stMainBlockContainer"]{
  padding:4.2rem 2rem 3rem 2rem !important;
  max-width:1600px !important;width:100% !important;margin:0 auto;box-sizing:border-box;}
/* let flex children shrink instead of pushing the page wider */
[data-testid="stColumn"], [data-testid="column"], [data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"] > div{min-width:0 !important;}
[data-testid="stPlotlyChart"], .js-plotly-plot, .plot-container, .svg-container{max-width:100% !important;}
[data-testid="stDataFrame"]{max-width:100%;}

/* ---------- sidebar ---------- */
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0b1f4b 0%,#1e40af 100%);}
@media (min-width:992px){[data-testid="stSidebar"]{min-width:270px !important;max-width:270px !important;}}
[data-testid="stSidebar"] *{color:#e8efff;}
[data-testid="stSidebar"] .stButton>button{width:100%;justify-content:flex-start;text-align:left;border:none;
 background:transparent;border-radius:10px;padding:.5rem .9rem;font-weight:500;box-shadow:none;}
[data-testid="stSidebar"] .stButton>button:hover{background:rgba(255,255,255,.14);}
[data-testid="stSidebar"] .stButton>button[kind="primary"],
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]{background:#ffffff;}
[data-testid="stSidebar"] button[kind="primary"] *,
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] *{color:#1e40af !important;font-weight:700;}
.brand{font-size:20px;font-weight:800;color:#fff;line-height:1.25;padding:10px 8px 0 8px;
 letter-spacing:.2px;overflow-wrap:anywhere;}
.brand-sub{font-size:12px;color:#a9c0f5;padding:0 8px 14px 8px;}
.brand-sub-head{padding-top:4px;margin-bottom:12px;border-bottom:1px solid rgba(255,255,255,.18);}

/* ---------- headings ---------- */
.page-title{font-size:clamp(22px,2.4vw,30px);font-weight:800;color:#0b1f4b;line-height:1.3;
 margin:0;padding-top:.2rem;overflow-wrap:anywhere;}
.page-sub{color:#64748b;margin:2px 0 18px 0;}

/* ---------- statistic cards: responsive CSS grid ---------- */
.stat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px;margin:0 0 16px 0;}
.stat-card{background:#fff;border-radius:16px;padding:16px 18px;box-shadow:0 2px 12px rgba(15,40,100,.08);
 border-left:6px solid var(--c);display:flex;align-items:center;gap:14px;min-width:0;overflow:hidden;}
.stat-icon{font-size:24px;min-width:50px;height:50px;border-radius:14px;display:flex;align-items:center;justify-content:center;}
.stat-card > div:last-child{min-width:0;}
.stat-val{font-size:clamp(20px,2.1vw,28px);font-weight:800;color:#0b1f4b;line-height:1.1;overflow-wrap:anywhere;}
.stat-lbl{font-size:13px;color:#64748b;margin-top:4px;}

/* ---------- badges, copy cards, queues ---------- */
.badge{display:inline-block;padding:3px 12px;border-radius:999px;font-size:12px;font-weight:700;color:#fff;}
.copy-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;margin:8px 0 14px 0;}
.copy-card{background:#fff;border-radius:14px;padding:14px;border-top:5px solid var(--c);
 box-shadow:0 2px 10px rgba(15,40,100,.08);min-width:0;overflow-wrap:anywhere;}
.copy-id{font-weight:700;color:#0b1f4b;font-size:13px;margin-bottom:8px;}
.copy-detail{font-size:12px;color:#475569;margin-top:8px;}
.queue-card{background:#fff;border-radius:14px;padding:14px 16px;box-shadow:0 2px 10px rgba(15,40,100,.08);margin-bottom:12px;}
.q-title{font-weight:700;color:#0b1f4b;margin-bottom:8px;overflow-wrap:anywhere;}
.q-row{display:flex;align-items:center;gap:10px;padding:7px 0;border-top:1px solid #eef2f7;}
.q-pos{background:#dbeafe;color:#1e40af;border-radius:50%;min-width:26px;height:26px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;}
.q-name{flex:1;color:#1e293b;min-width:0;overflow-wrap:anywhere;}
.legend{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px;}
div.stButton>button,[data-testid="stFormSubmitButton"]>button{border-radius:10px;font-weight:600;}

/* ---------- laptop / tablet: let columns wrap instead of squeezing ---------- */
@media (max-width:1100px){
  [data-testid="stHorizontalBlock"]{flex-wrap:wrap !important;}
  [data-testid="stColumn"], [data-testid="column"]{flex:1 1 320px !important;min-width:min(100%,320px) !important;}
  .block-container, [data-testid="stMainBlockContainer"]{padding:4rem 1.2rem 2rem 1.2rem !important;}
}
/* ---------- phones ---------- */
@media (max-width:640px){
  .stat-grid{grid-template-columns:1fr 1fr;gap:10px;}
  .stat-card{padding:12px;gap:10px;}
  .stat-icon{min-width:40px;height:40px;font-size:20px;}
  .block-container, [data-testid="stMainBlockContainer"]{padding:3.6rem .7rem 2rem .7rem !important;}
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ------------------------------------------------------------------ UI helpers
def badge(text, color):
    return f'<span class="badge" style="background:{color}">{escape(str(text))}</span>'


def stat_card(label, value, icon, color):
    return (f'<div class="stat-card" style="--c:{color}"><div class="stat-icon" style="background:{color}22">{icon}</div>'
            f'<div><div class="stat-val">{value}</div><div class="stat-lbl">{label}</div></div></div>')


def stat_grid(cards):
    """cards = list of (label, value, icon, color). Renders a responsive CSS grid."""
    st.markdown('<div class="stat-grid">' + "".join(stat_card(*c) for c in cards) + "</div>", unsafe_allow_html=True)


def header(title, sub=""):
    st.markdown(f'<div class="page-title">{title}</div><div class="page-sub">{sub}</div>', unsafe_allow_html=True)


def legend():
    items = "".join(badge(f"{EMOJI[s]} {s}", COLORS[s]) for s in STATUSES)
    st.markdown(f'<div class="legend">{items}</div>', unsafe_allow_html=True)


def plot(fig, h=340):
    """Style a Plotly figure and make it fill its container (works on old and new Streamlit)."""
    fig.update_layout(template="plotly_white", height=h, autosize=True, margin=dict(l=10, r=10, t=45, b=10),
                      title_font_size=16, legend=dict(orientation="h", y=-0.15), paper_bgcolor="rgba(0,0,0,0)")
    try:
        st.plotly_chart(fig, width="stretch")
    except TypeError:  # older Streamlit versions
        st.plotly_chart(fig, use_container_width=True)


def flash(ok, msg, log=None):
    st.session_state["flash"] = (ok, msg, log)
    st.rerun()


def done(res):
    flash(res["ok"], res["message"], res.get("log"))


def show_flash():
    f = st.session_state.pop("flash", None)
    if f:
        ok, msg, log = f
        (st.success if ok else st.error)(msg)
        if log:
            with st.expander("🔒 Mutex / critical-section log", expanded=True):
                st.code("\n".join(log), language="text")


# ------------------------------------------------------------------ data helpers
BOOK_COLS = ["book_id", "isbn", "title", "author", "category", "publisher", "total_copies",
             "available", "issued", "reserved", "disabled", "shelf"]
TX_COLS = ["txn_id", "student_id", "student", "book_id", "title", "copy_id", "issue_date", "due_date",
           "return_date", "status", "overdue_days", "fine_amount"]
STU_COLS = ["student_id", "name", "department", "email", "phone", "registered"]


def books_df():
    copies, rows = storage.load("copies"), []
    for b in storage.load("books"):
        mine = [c for c in copies if c["book_id"] == b["book_id"]]
        r = dict(b)
        r["total_copies"] = len(mine)
        for s in STATUSES:
            r[s.lower()] = sum(1 for c in mine if c["status"] == s)
        rows.append(r)
    return pd.DataFrame(rows, columns=BOOK_COLS)


def students_df():
    return pd.DataFrame(storage.load("students"), columns=STU_COLS)


def txn_df():
    names = {s["student_id"]: s["name"] for s in storage.load("students")}
    titles = {b["book_id"]: b["title"] for b in storage.load("books")}
    today, rows = date.today(), []
    for t in storage.load("transactions"):
        r = dict(t)
        r["student"] = names.get(t["student_id"], "(deleted)")
        r["title"] = titles.get(t["book_id"], "(deleted)")
        if t["status"] == "Issued":
            od = max(0, (today - date.fromisoformat(t["due_date"])).days)
            r["overdue_days"], r["fine_amount"] = od, od * svc.FINE_PER_DAY
        else:
            r["overdue_days"], r["fine_amount"] = 0, t.get("fine", 0)
        rows.append(r)
    return pd.DataFrame(rows, columns=TX_COLS)


def tx_view(df, cols=None):
    v = df.copy()
    v["status"] = v["status"].map({"Issued": "📘 Issued", "Returned": "✅ Returned"})
    v["return_date"] = v["return_date"].fillna("—")
    v = v[cols or ["txn_id", "student", "title", "copy_id", "issue_date", "due_date", "return_date", "status", "fine_amount"]]
    return v.rename(columns={"txn_id": "Txn ID", "student": "Student", "title": "Book", "copy_id": "Copy ID",
                             "issue_date": "Issued", "due_date": "Due", "return_date": "Returned",
                             "status": "Status", "fine_amount": "Fine (₹)", "overdue_days": "Days Overdue",
                             "student_id": "Student ID", "book_id": "Book ID"})


def filter_books(df, q="", by="All fields", cats=None, only_available=False):
    out = df
    if q:
        cols = {"All fields": ["title", "author", "isbn", "book_id"], "Title": ["title"],
                "Author": ["author"], "ISBN": ["isbn"]}[by]
        mask = pd.Series(False, index=out.index)
        for c in cols:
            mask = mask | out[c].astype(str).str.lower().str.contains(q.lower(), regex=False)
        out = out[mask]
    if cats:
        out = out[out["category"].isin(cats)]
    if only_available:
        out = out[out["available"] > 0]
    return out


def copy_cards(book_id):
    copies = [c for c in storage.load("copies") if c["book_id"] == book_id]
    names = {s["student_id"]: s["name"] for s in storage.load("students")}
    shelf = (next((b["shelf"] for b in storage.load("books") if b["book_id"] == book_id), ""))
    active = {t["copy_id"]: t for t in storage.load("transactions") if t["status"] == "Issued"}
    ready = {r["copy_id"]: r for r in storage.load("reservations") if r["status"] == "Ready"}
    html = '<div class="copy-grid">'
    for c in copies:
        s = c["status"]
        if s == "Issued" and c["copy_id"] in active:
            t = active[c["copy_id"]]
            detail = f"Borrower: {escape(names.get(t['student_id'], t['student_id']))}<br>Due: {t['due_date']}"
        elif s == "Reserved" and c["copy_id"] in ready:
            detail = f"Held for: {escape(names.get(ready[c['copy_id']]['student_id'], '?'))}"
        elif s == "Available":
            detail = f"On shelf {escape(shelf)}"
        else:
            detail = "Temporarily unavailable"
        html += (f'<div class="copy-card" style="--c:{COLORS[s]}"><div class="copy-id">{c["copy_id"]}</div>'
                 f'{badge(EMOJI[s] + " " + s, COLORS[s])}<div class="copy-detail">{detail}</div></div>')
    st.markdown(html + "</div>", unsafe_allow_html=True)


# ------------------------------------------------------------------ pages
def page_dashboard():
    header("Dashboard Overview", "Live statistics calculated from the JSON data files")
    books, copies = books_df(), storage.load("copies")
    students, tx, resv = storage.load("students"), txn_df(), storage.load("reservations")
    n = lambda s: sum(1 for c in copies if c["status"] == s)
    open_res = sum(1 for r in resv if r["status"] in ("Pending", "Ready"))
    done_tx = int((tx["status"] == "Returned").sum())
    stat_grid([("Total Books", len(books), "📚", "#2563eb"), ("Physical Copies", len(copies), "🗂️", "#1e40af"),
               ("Available Copies", n("Available"), "✅", "#16a34a"), ("Issued Copies", n("Issued"), "📤", "#dc2626"),
               ("Registered Students", len(students), "🎓", "#0891b2"), ("Pending Reservations", open_res, "⏳", "#f97316"),
               ("Completed Transactions", done_tx, "🧾", "#7c3aed")])

    c1, c2 = st.columns(2)
    with c1, st.container(border=True):
        data = pd.DataFrame({"Status": STATUSES, "Copies": [n(s) for s in STATUSES]})
        plot(px.pie(data, names="Status", values="Copies", hole=0.55, color="Status",
                    color_discrete_map=COLORS, title="Available vs Issued Copies"))
    with c2, st.container(border=True):
        if tx.empty:
            st.info("No transactions yet.")
        else:
            m = tx.assign(Month=pd.to_datetime(tx["issue_date"]).dt.strftime("%Y-%m")).groupby("Month").size().reset_index(name="Books Issued")
            plot(px.bar(m, x="Month", y="Books Issued", title="Monthly Book Issue Activity",
                        color_discrete_sequence=["#2563eb"]))
    c3, c4 = st.columns([3, 2])
    with c3, st.container(border=True):
        if tx.empty:
            st.info("No transactions yet.")
        else:
            p = tx.groupby("title").size().reset_index(name="Issues").sort_values("Issues").tail(6)
            fig = px.bar(p, x="Issues", y="title", orientation="h", color="Issues", color_continuous_scale="Blues",
                         title="Most Popular Books")
            fig.update_coloraxes(showscale=False)
            fig.update_yaxes(title="")
            plot(fig)
    with c4, st.container(border=True):
        st.markdown("##### 📌 Reservation Summary")
        colr = {"Pending": "#2563eb", "Ready": "#f97316", "Fulfilled": "#16a34a", "Cancelled": "#6b7280"}
        for s, col in colr.items():
            k = sum(1 for r in resv if r["status"] == s)
            st.markdown(f"{badge(s, col)} &nbsp; **{k}**", unsafe_allow_html=True)
    st.markdown("##### 🕒 Recent Transactions")
    if tx.empty:
        st.info("No transactions yet.")
    else:
        st.dataframe(tx_view(tx.sort_values("txn_id", ascending=False).head(8)), hide_index=True)


def page_books():
    header("Book Management", "Add, update, search and remove books")
    df = books_df()
    t1, t2, t3 = st.tabs(["📋 All Books", "➕ Add Book", "✏️ Update / Delete"])
    with t1:
        c1, c2, c3 = st.columns([3, 2, 3])
        q = c1.text_input("🔍 Search", key="bm_q", placeholder="Type to search...")
        by = c2.selectbox("Search by", ["All fields", "Title", "Author", "ISBN"], key="bm_by")
        cats = c3.multiselect("Category", sorted(df["category"].unique()), key="bm_cat")
        out = filter_books(df, q, by, cats).copy()
        out["status"] = out["available"].apply(lambda a: "🟢 In stock" if a > 0 else "🔴 All issued")
        st.caption(f"{len(out)} book(s) found")
        st.dataframe(out.rename(columns={"book_id": "Book ID", "isbn": "ISBN", "title": "Title", "author": "Author",
                                         "category": "Category", "publisher": "Publisher", "total_copies": "Total",
                                         "available": "Available", "issued": "Issued", "reserved": "Reserved",
                                         "disabled": "Disabled", "shelf": "Shelf", "status": "Stock"}), hide_index=True)
    with t2:
        with st.form("add_book", clear_on_submit=True):
            a, b = st.columns(2)
            title, author = a.text_input("Book title *"), b.text_input("Author *")
            isbn, cat = a.text_input("ISBN"), b.text_input("Category", value="General")
            pub, shelf = a.text_input("Publisher"), b.text_input("Shelf location")
            total = a.number_input("Total copies", min_value=1, value=1, step=1)
            if st.form_submit_button("➕ Add Book", type="primary"):
                done(svc.add_book(isbn, title, author, cat, pub, int(total), shelf))
    with t3:
        if df.empty:
            st.info("No books yet.")
            return
        titles = dict(zip(df["book_id"], df["title"]))
        bid = st.selectbox("Select book", df["book_id"].tolist(), format_func=lambda x: f"{x} — {titles[x]}", key="upd_book")
        row = df[df["book_id"] == bid].iloc[0]
        with st.form(f"upd_{bid}"):
            a, b = st.columns(2)
            title = a.text_input("Title", row["title"], key=f"ut_{bid}")
            author = b.text_input("Author", row["author"], key=f"ua_{bid}")
            isbn = a.text_input("ISBN", row["isbn"], key=f"ui_{bid}")
            cat = b.text_input("Category", row["category"], key=f"uc_{bid}")
            pub = a.text_input("Publisher", row["publisher"], key=f"up_{bid}")
            shelf = b.text_input("Shelf", row["shelf"], key=f"us_{bid}")
            total = a.number_input("Total copies", min_value=1, value=int(row["total_copies"]), key=f"un_{bid}")
            if st.form_submit_button("💾 Save Changes", type="primary"):
                done(svc.update_book(bid, isbn, title, author, cat, pub, int(total), shelf))
        st.markdown("##### 🗑️ Delete this book")
        ok = st.checkbox("I confirm I want to delete this book and all its copies", key=f"dc_{bid}")
        if st.button("Delete Book", key=f"db_{bid}", disabled=not ok):
            done(svc.delete_book(bid))


def page_students():
    header("Student Management", "Register students and view their borrowing history")
    df = students_df()
    t1, t2, t3, t4 = st.tabs(["📋 All Students", "➕ Register", "✏️ Update / Delete", "📜 Borrowing History"])
    with t1:
        c1, c2 = st.columns([3, 2])
        q = c1.text_input("🔍 Search students", key="sm_q", placeholder="Name, ID, email...")
        dept = c2.multiselect("Department", sorted(df["department"].unique()), key="sm_d")
        out = df
        if q:
            out = out[out.apply(lambda r: q.lower() in " ".join(map(str, r.values)).lower(), axis=1)]
        if dept:
            out = out[out["department"].isin(dept)]
        st.caption(f"{len(out)} student(s) found")
        st.dataframe(out.rename(columns={"student_id": "Student ID", "name": "Name", "department": "Department",
                                         "email": "Email", "phone": "Phone", "registered": "Registered"}), hide_index=True)
    with t2:
        with st.form("reg_student", clear_on_submit=True):
            a, b = st.columns(2)
            name, dep = a.text_input("Full name *"), b.text_input("Department", value="CSE")
            email, phone = a.text_input("Email *"), b.text_input("Phone (10 digits) *")
            if st.form_submit_button("➕ Register Student", type="primary"):
                done(svc.register_student(name, dep, email, phone))
    names = dict(zip(df["student_id"], df["name"]))
    with t3:
        if df.empty:
            st.info("No students yet.")
        else:
            sid = st.selectbox("Select student", df["student_id"].tolist(), format_func=lambda x: f"{x} — {names[x]}", key="upd_stu")
            row = df[df["student_id"] == sid].iloc[0]
            with st.form(f"us_form_{sid}"):
                a, b = st.columns(2)
                name = a.text_input("Name", row["name"], key=f"sn_{sid}")
                dep = b.text_input("Department", row["department"], key=f"sd_{sid}")
                email = a.text_input("Email", row["email"], key=f"se_{sid}")
                phone = b.text_input("Phone", row["phone"], key=f"sp_{sid}")
                if st.form_submit_button("💾 Save Changes", type="primary"):
                    done(svc.update_student(sid, name, dep, email, phone))
            ok = st.checkbox("I confirm I want to delete this student", key=f"sdc_{sid}")
            if st.button("🗑️ Delete Student", key=f"sdb_{sid}", disabled=not ok):
                done(svc.delete_student(sid))
    with t4:
        if df.empty:
            st.info("No students yet.")
        else:
            sid = st.selectbox("Student", df["student_id"].tolist(), format_func=lambda x: f"{x} — {names[x]}", key="hist_stu")
            tx = txn_df()
            tx = tx[tx["student_id"] == sid]
            stat_grid([("Total Borrowed", len(tx), "📚", "#2563eb"),
                       ("Currently Issued", int((tx["status"] == "Issued").sum()), "📘", "#dc2626"),
                       ("Fines (₹)", int(tx["fine_amount"].sum()), "💰", "#f97316")])
            st.dataframe(tx_view(tx), hide_index=True)


def page_search():
    header("Search Books", "Find books and check live copy availability")
    df = books_df()
    c1, c2, c3 = st.columns([3, 2, 3])
    q = c1.text_input("🔍 Search", key="sb_q", placeholder="Title, author or ISBN")
    by = c2.selectbox("Search by", ["All fields", "Title", "Author", "ISBN"], key="sb_by")
    cats = c3.multiselect("Category", sorted(df["category"].unique()), key="sb_c")
    only = st.toggle("Show only books with available copies", key="sb_only")
    out = filter_books(df, q, by, cats, only).copy()
    st.caption(f"{len(out)} result(s)")
    out["Stock"] = out["available"].apply(lambda a: "🟢 Available" if a > 0 else "🔴 Unavailable")
    st.dataframe(out[["book_id", "title", "author", "isbn", "category", "shelf", "available", "total_copies", "Stock"]]
                 .rename(columns={"book_id": "Book ID", "title": "Title", "author": "Author", "isbn": "ISBN",
                                  "category": "Category", "shelf": "Shelf", "available": "Available",
                                  "total_copies": "Total"}), hide_index=True)
    if not out.empty:
        titles = dict(zip(out["book_id"], out["title"]))
        bid = st.selectbox("View physical copies of", out["book_id"].tolist(), format_func=lambda x: titles[x], key="sb_view")
        legend()
        copy_cards(bid)


def page_issue():
    header("Issue Books", "Protected by a mutex lock so the last copy can never be issued twice")
    students, bdf = students_df(), books_df()
    if students.empty or bdf.empty:
        st.warning("Register at least one student and add one book first.")
        return
    sn = dict(zip(students["student_id"], students["name"]))
    left, right = st.columns([2, 3])
    with left, st.container(border=True):
        st.markdown("#### 📝 Issue Details")
        sid = st.selectbox("Student", students["student_id"].tolist(), format_func=lambda x: f"{x} — {sn[x]}", key="is_stu")
        q = st.text_input("🔍 Filter books", key="is_q", placeholder="Title / author / ISBN")
        fb = filter_books(bdf, q)
        if fb.empty:
            st.warning("No matching books.")
            return
        info = {r["book_id"]: r for _, r in fb.iterrows()}
        bid = st.selectbox("Book", list(info), key="is_book",
                           format_func=lambda x: f"{info[x]['title']}  ({info[x]['available']} available)")
        st.caption(f"📅 Due date will be {date.today() + timedelta(days=svc.LOAN_DAYS)} ({svc.LOAN_DAYS} days)")
        if st.button("📤 Issue Book", type="primary", key="do_issue"):
            done(svc.issue_book(sid, bid, who=f"{sid}"))
    with right, st.container(border=True):
        row = info[bid]
        st.markdown(f"#### 📖 {escape(row['title'])}")
        st.caption(f"{row['author']} · {row['category']} · Shelf {row['shelf']}")
        if any(r["student_id"] == sid and r["book_id"] == bid and r["status"] == "Ready" for r in storage.load("reservations")):
            st.info("⭐ This student has a reserved copy waiting and will receive it.")
        legend()
        copy_cards(bid)


def page_return():
    header("Return Books", "Process returns and calculate late fines automatically")
    tx = txn_df()
    act = tx[tx["status"] == "Issued"]
    if act.empty:
        st.success("🎉 No books are currently issued.")
        return
    q = st.text_input("🔍 Filter by student, book or transaction ID", key="rt_q")
    if q:
        act = act[act.apply(lambda r: q.lower() in f"{r['student']} {r['title']} {r['txn_id']}".lower(), axis=1)]
    if act.empty:
        st.warning("No matching issued books.")
        return
    rows = {r["txn_id"]: r for _, r in act.iterrows()}
    tid = st.selectbox("Select issued book", list(rows), key="rt_sel",
                       format_func=lambda x: f"{x} — {rows[x]['title']} → {rows[x]['student']}")
    r = rows[tid]
    stat_grid([("Student", escape(r["student"]), "🎓", "#2563eb"),
               ("Copy", escape(r["copy_id"][-7:]), "📘", "#1e40af"),
               ("Due Date", r["due_date"], "📅", "#dc2626" if r["overdue_days"] else "#16a34a"),
               ("Fine Today (₹)", r["fine_amount"], "💰", "#f97316")])
    if r["overdue_days"]:
        st.warning(f"This book is {r['overdue_days']} day(s) overdue.")
    if st.button("📥 Return Book", type="primary", key="do_return"):
        done(svc.return_book(tid))


def queue_html(title, items, names):
    rows = ""
    for i, r in enumerate(items, 1):
        b = badge("Ready for pickup", "#f97316") if r["status"] == "Ready" else badge("Waiting", "#2563eb")
        rows += (f'<div class="q-row"><span class="q-pos">{i}</span>'
                 f'<span class="q-name">{escape(names.get(r["student_id"], r["student_id"]))} · {r["res_id"]}</span>{b}</div>')
    return f'<div class="queue-card"><div class="q-title">📖 {escape(title)}</div>{rows}</div>'


def page_reservations():
    header("Book Reservations", "Join the queue when every copy is issued")
    students, bdf = students_df(), books_df()
    sn, bt = dict(zip(students["student_id"], students["name"])), dict(zip(bdf["book_id"], bdf["title"]))
    resv = storage.load("reservations")
    t1, t2, t3 = st.tabs(["📌 Reserve a Book", "🧾 Reservation Queues", "⚙️ Manage"])
    with t1:
        if students.empty or bdf.empty:
            st.warning("Need at least one student and one book.")
        else:
            sid = st.selectbox("Student", students["student_id"].tolist(), format_func=lambda x: f"{x} — {sn[x]}", key="rv_stu")
            av = dict(zip(bdf["book_id"], bdf["available"]))
            bid = st.selectbox("Book", bdf["book_id"].tolist(), key="rv_book",
                               format_func=lambda x: f"{bt[x]}  ({av[x]} available)")
            st.caption("Reservations are only accepted when no copy is available.")
            if st.button("📌 Reserve", type="primary", key="do_res"):
                done(svc.reserve_book(sid, bid))
    with t2:
        openr = [r for r in resv if r["status"] in ("Pending", "Ready")]
        if not openr:
            st.info("No open reservations.")
        for bid in dict.fromkeys(r["book_id"] for r in openr):
            st.markdown(queue_html(bt.get(bid, bid), [r for r in openr if r["book_id"] == bid], sn), unsafe_allow_html=True)
    with t3:
        openr = [r for r in resv if r["status"] in ("Pending", "Ready")]
        if openr:
            rid = st.selectbox("Cancel a reservation", [r["res_id"] for r in openr], key="rv_cancel",
                               format_func=lambda x: f"{x} — {bt.get(find_r(resv, x)['book_id'], '?')} / {sn.get(find_r(resv, x)['student_id'], '?')}")
            if st.button("❌ Cancel Reservation", key="do_cancel"):
                done(svc.cancel_reservation(rid))
        if resv:
            v = pd.DataFrame(resv)
            v["student"] = v["student_id"].map(sn)
            v["book"] = v["book_id"].map(bt)
            v["status"] = v["status"].map({"Pending": "🔵 Pending", "Ready": "🟠 Ready", "Fulfilled": "✅ Fulfilled", "Cancelled": "⚪ Cancelled"})
            st.dataframe(v[["res_id", "student", "book", "date", "status"]].rename(columns={
                "res_id": "Reservation", "student": "Student", "book": "Book", "date": "Date", "status": "Status"}),
                hide_index=True)


def find_r(resv, rid):
    return next(r for r in resv if r["res_id"] == rid)


def page_issued():
    header("Issued Books", "All books currently out of the library")
    tx = txn_df()
    act = tx[tx["status"] == "Issued"].copy()
    stat_grid([("Currently Issued", len(act), "📘", "#2563eb"),
               ("Overdue", int((act["overdue_days"] > 0).sum()), "⚠️", "#dc2626"),
               ("Pending Fines (₹)", int(act["fine_amount"].sum()), "💰", "#f97316")])
    q = st.text_input("🔍 Filter by student or book", key="ib_q")
    only = st.toggle("Show only overdue", key="ib_over")
    if q:
        act = act[act.apply(lambda r: q.lower() in f"{r['student']} {r['title']}".lower(), axis=1)]
    if only:
        act = act[act["overdue_days"] > 0]
    act["Condition"] = act["overdue_days"].apply(lambda d: "🔴 Overdue" if d > 0 else "🟢 On time")
    v = tx_view(act, ["txn_id", "student", "title", "copy_id", "issue_date", "due_date", "overdue_days", "fine_amount"])
    v["Condition"] = act["Condition"].values
    st.dataframe(v, hide_index=True)


def page_availability():
    header("Availability Monitoring", "Status of every individual physical copy")
    copies = storage.load("copies")
    icons = {"Available": "✅", "Issued": "📤", "Reserved": "🟠", "Disabled": "⛔"}
    stat_grid([(s, sum(1 for c in copies if c["status"] == s), icons[s], COLORS[s]) for s in STATUSES])
    legend()
    bdf = books_df()
    for _, b in bdf.iterrows():
        with st.expander(f"📖 {b['title']} — {b['available']}/{b['total_copies']} available", expanded=False):
            copy_cards(b["book_id"])
    st.markdown("---")
    st.markdown("#### 🔧 Enable / Disable a Copy")
    togg = [c for c in copies if c["status"] in ("Available", "Disabled")]
    if togg:
        cid = st.selectbox("Copy", [c["copy_id"] for c in togg], key="tg_copy",
                           format_func=lambda x: f"{x} ({find_c(copies, x)['status']})")
        if find_c(copies, cid)["status"] == "Available":
            if st.button("⛔ Disable copy", key="do_dis"):
                done(svc.set_copy_disabled(cid, True))
        elif st.button("✅ Enable copy", key="do_en"):
            done(svc.set_copy_disabled(cid, False))
    st.markdown("---")
    st.markdown("#### 🧪 Race Condition Demo: two students, one last copy")
    st.caption("Two threads request the same book at the same instant. The mutex lets only one in at a time. "
               "This demo really issues the copy, so return it afterwards from the Return page.")
    students = students_df()
    if len(students) < 2 or bdf.empty:
        st.info("Need at least 2 students and 1 book.")
        return
    sn = dict(zip(students["student_id"], students["name"]))
    one = bdf[bdf["available"] == 1]
    pool = one if not one.empty else bdf
    bt = dict(zip(bdf["book_id"], bdf["title"]))
    av = dict(zip(bdf["book_id"], bdf["available"]))
    c1, c2, c3 = st.columns(3)
    bid = c1.selectbox("Book (pick one with 1 available copy)", pool["book_id"].tolist(), key="rc_book",
                       format_func=lambda x: f"{bt[x]} ({av[x]} available)")
    sa = c2.selectbox("Student A", students["student_id"].tolist(), index=0, key="rc_a", format_func=lambda x: sn[x])
    sb = c3.selectbox("Student B", students["student_id"].tolist(), index=1, key="rc_b", format_func=lambda x: sn[x])
    delay = st.slider("Simulated processing delay inside the critical section (seconds)", 0.0, 1.5, 0.4, 0.1)
    if st.button("▶ Run simultaneous request test", type="primary", key="do_race"):
        if sa == sb:
            st.error("Choose two different students.")
            return
        results, barrier = {}, threading.Barrier(2)

        def worker(label, sid):
            barrier.wait()  # both threads start together
            results[label] = svc.issue_book(sid, bid, delay=delay, who=label)

        ths = [threading.Thread(target=worker, args=(lbl, s), name=lbl) for lbl, s in (("Student A", sa), ("Student B", sb))]
        for t in ths:
            t.start()
        for t in ths:
            t.join()
        wins = sum(1 for r in results.values() if r["ok"])
        for lbl in ("Student A", "Student B"):
            (st.success if results[lbl]["ok"] else st.error)(f"{lbl}: {results[lbl]['message']}")
        if av[bid] == 1 and wins == 1:
            st.success("✅ Mutual exclusion worked: exactly one student got the last copy, with no duplicate issue.")
        elif av[bid] > 1:
            st.info("This book had more than one free copy, so both succeeded. Pick a book with 1 available copy to see the race.")
        logs = sorted(results["Student A"]["log"] + results["Student B"]["log"])
        st.code("\n".join(logs), language="text")


def find_c(copies, cid):
    return next(c for c in copies if c["copy_id"] == cid)


def page_history():
    header("Transaction History", "Search, filter and export every issue and return")
    tx = txn_df()
    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
    q = c1.text_input("🔍 Search", key="th_q", placeholder="Student, book, Txn ID...")
    stt = c2.selectbox("Status", ["All", "Issued", "Returned"], key="th_s")
    d1 = c3.date_input("From", date.today() - timedelta(days=365), key="th_d1")
    d2 = c4.date_input("To", date.today(), key="th_d2")
    out = tx
    if q:
        out = out[out.apply(lambda r: q.lower() in f"{r['txn_id']} {r['student']} {r['title']} {r['copy_id']}".lower(), axis=1)]
    if stt != "All":
        out = out[out["status"] == stt]
    dates = pd.to_datetime(out["issue_date"]).dt.date
    out = out[(dates >= d1) & (dates <= d2)]
    st.caption(f"{len(out)} transaction(s)")
    st.dataframe(tx_view(out.sort_values("txn_id", ascending=False)), hide_index=True)
    st.download_button("⬇️ Export CSV", out.to_csv(index=False).encode("utf-8"), "transactions.csv", "text/csv")


def page_reports():
    header("Reports & Analytics", "Interactive charts built from live JSON data")
    tx, bdf, sdf = txn_df(), books_df(), students_df()
    stat_grid([("Total Transactions", len(tx), "🧾", "#2563eb"),
               ("Active Issues", int((tx["status"] == "Issued").sum()), "📘", "#dc2626"),
               ("Overdue Now", int((tx["overdue_days"] > 0).sum()), "⚠️", "#f97316"),
               ("Total Fines (₹)", int(tx["fine_amount"].sum()), "💰", "#7c3aed")])
    if tx.empty:
        st.info("No transactions to analyse yet.")
    else:
        a, b = st.columns(2)
        with a, st.container(border=True):
            iss = tx.assign(Month=pd.to_datetime(tx["issue_date"]).dt.strftime("%Y-%m")).groupby("Month").size().rename("Issued")
            ret = tx[tx["return_date"].notna()].assign(Month=lambda d: pd.to_datetime(d["return_date"]).dt.strftime("%Y-%m")).groupby("Month").size().rename("Returned")
            m = pd.concat([iss, ret], axis=1).fillna(0).reset_index()
            plot(px.line(m, x="Month", y=["Issued", "Returned"], markers=True, title="Issues vs Returns by Month",
                         color_discrete_sequence=["#2563eb", "#16a34a"]))
        with b, st.container(border=True):
            dm = dict(zip(sdf["student_id"], sdf["department"]))
            d = tx.assign(Department=tx["student_id"].map(dm).fillna("Unknown")).groupby("Department").size().reset_index(name="Issues")
            plot(px.bar(d, x="Department", y="Issues", title="Issues by Department",
                        color="Issues", color_continuous_scale="Blues"))
        a, b = st.columns(2)
        with a, st.container(border=True):
            cat = dict(zip(bdf["book_id"], bdf["category"]))
            k = tx.assign(Category=tx["book_id"].map(cat).fillna("Unknown")).groupby("Category").size().reset_index(name="Issues")
            plot(px.pie(k, names="Category", values="Issues", hole=0.45, title="Issues by Category",
                        color_discrete_sequence=px.colors.sequential.Blues_r))
        with b, st.container(border=True):
            s = tx.groupby("student").size().reset_index(name="Books").sort_values("Books").tail(6)
            plot(px.bar(s, x="Books", y="student", orientation="h", title="Top Borrowers",
                        color_discrete_sequence=["#1e40af"]))
    if not bdf.empty:
        with st.container(border=True):
            long = bdf.melt(id_vars="title", value_vars=[s.lower() for s in STATUSES], var_name="Status", value_name="Copies")
            long["Status"] = long["Status"].str.capitalize()
            plot(px.bar(long, x="title", y="Copies", color="Status", color_discrete_map=COLORS,
                        title="Copy Status by Book", barmode="stack"), 380)
    st.markdown("##### ⬇️ Export data")
    d1, d2, d3 = st.columns(3)
    d1.download_button("Books CSV", bdf.to_csv(index=False).encode(), "books.csv", "text/csv")
    d2.download_button("Students CSV", sdf.to_csv(index=False).encode(), "students.csv", "text/csv")
    d3.download_button("Transactions CSV", tx.to_csv(index=False).encode(), "transactions.csv", "text/csv")


def page_about():
    header("About Project", "Library Book Issue and Reservation System")
    st.markdown("""
**Problem solved:** two users request the last available copy of a book at the same time. Without protection, both
could read "1 copy available" and both be issued the same copy. This is a classic **race condition**.

**Solution:** every operation that changes data runs inside a **critical section** guarded by a
`threading.Lock()` (a **mutex**). Only one thread can hold the lock, which gives **mutual exclusion**.
""")
    st.code("""LOCK = threading.Lock()

def issue_book(student_id, book_id):
    with LOCK:                     # acquire mutex -> enter critical section
        # 1. check availability   2. mark copy Issued
        # 3. record transaction   4. save JSON
        ...                        # lock released automatically on exit
""", language="python")
    st.markdown("""
**Technology:** Python · Streamlit · JSON files · Pandas · Plotly · `threading.Lock()` · `datetime`

**OS concepts:** Critical Section · Mutex Lock · Mutual Exclusion · Race Condition Prevention · Thread Synchronization

**Try it:** Availability Monitoring → *Race Condition Demo*.
""")


# ------------------------------------------------------------------ navigation
PAGES = [("📊", "Dashboard Overview", page_dashboard), ("📚", "Book Management", page_books),
         ("🎓", "Student Management", page_students), ("🔍", "Search Books", page_search),
         ("📤", "Issue Books", page_issue), ("📥", "Return Books", page_return),
         ("📌", "Book Reservations", page_reservations), ("📘", "Issued Books", page_issued),
         ("🟢", "Availability Monitoring", page_availability), ("🧾", "Transaction History", page_history),
         ("📈", "Reports and Analytics", page_reports), ("ℹ️", "About Project", page_about)]

st.session_state.setdefault("page", PAGES[0][1])
with st.sidebar:
    st.markdown('<div class="brand">Library Management System</div>'
                '<div class="brand-sub brand-sub-head">Library Management Platform</div>', unsafe_allow_html=True)
    for icon, name, _ in PAGES:
        active = st.session_state["page"] == name
        if st.button(f"{icon}  {name}", key=f"nav_{name}", type="primary" if active else "secondary"):
            st.session_state["page"] = name
            st.rerun()
    st.markdown(f'<div class="brand-sub" style="padding-top:18px">📅 {date.today():%d %b %Y}<br>🔒 Mutex-protected operations</div>',
                unsafe_allow_html=True)

show_flash()
dict((n, f) for _, n, f in PAGES)[st.session_state["page"]]()