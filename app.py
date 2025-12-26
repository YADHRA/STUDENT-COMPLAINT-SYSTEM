from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

DB_NAME = "database.db"

def get_db():
    return sqlite3.connect(DB_NAME)

# ---------------- DATABASE SETUP ----------------
def init_db():
    db = get_db()
    cur = db.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        type TEXT,
        description TEXT,
        status TEXT DEFAULT 'Pending',
        created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # default admin
    cur.execute("SELECT * FROM users WHERE role='admin'")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (username,password,role) VALUES (?,?,?)",
            ("admin", generate_password_hash("admin123"), "admin")
        )

    db.commit()
    db.close()

init_db()

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("home.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cur.fetchone()
        db.close()

        if user and check_password_hash(user[2], password):
            session["user_id"] = user[0]
            session["role"] = user[3]
            return redirect("/admin" if user[3] == "admin" else "/student")
        else:
            flash("Invalid username or password", "error")

    return render_template("login.html")

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        try:
            db = get_db()
            cur = db.cursor()
            cur.execute(
                "INSERT INTO users (username,password,role) VALUES (?,?,?)",
                (username, password, "student")
            )
            db.commit()
            db.close()
            flash("Registration successful!", "success")
            return redirect("/login")
        except:
            flash("Username already exists", "error")

    return render_template("register.html")

# ---------------- STUDENT DASHBOARD ----------------
@app.route("/student", methods=["GET", "POST"])
def student_dashboard():
    if session.get("role") != "student":
        return redirect("/login")

    if request.method == "POST":
        ctype = request.form["type"]
        desc = request.form["description"]
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        db = get_db()
        cur = db.cursor()
        cur.execute("""
            INSERT INTO complaints (user_id, type, description, created_at)
            VALUES (?, ?, ?, ?)
        """, (session["user_id"], ctype, desc, date))
        db.commit()
        db.close()
        flash("Complaint submitted successfully!", "success")

    # 🔧 UPDATED QUERY (IMPORTANT CHANGE)
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT type, description, status, created_at
        FROM complaints
        WHERE user_id=?
        ORDER BY id DESC
    """, (session["user_id"],))
    complaints = cur.fetchall()
    db.close()

    return render_template("student_dashboard.html", complaints=complaints)

# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin", methods=["GET", "POST"])
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect("/login")

    db = get_db()
    cur = db.cursor()

    if request.method == "POST":
        cid = request.form["cid"]
        status = request.form["status"]
        cur.execute("UPDATE complaints SET status=? WHERE id=?", (status, cid))
        db.commit()

    cur.execute("""
        SELECT complaints.*, users.username
        FROM complaints
        JOIN users ON complaints.user_id = users.id
        ORDER BY complaints.id DESC
    """)
    complaints = cur.fetchall()
    db.close()

    return render_template("admin_dashboard.html", complaints=complaints)

# ---------------- ABOUT PAGE ----------------
@app.route("/about")
def about():
    return render_template("about.html")

# ---------------- PROFILE PAGE ----------------
@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect("/login")

    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT username, role FROM users WHERE id=?", (session["user_id"],))
    user = cur.fetchone()
    username, role = user

    if role == "student":
        cur.execute("SELECT COUNT(*) FROM complaints WHERE user_id=?", (session["user_id"],))
        total = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM complaints WHERE user_id=? AND status='Solved'", (session["user_id"],))
        solved = cur.fetchone()[0]

        return render_template(
            "profile.html",
            username=username,
            role=role,
            total=total,
            solved=solved
        )
    else:
        cur.execute("SELECT COUNT(*) FROM complaints")
        total_handled = cur.fetchone()[0]

        return render_template(
            "profile.html",
            username=username,
            role=role,
            total_handled=total_handled
        )

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
# ---------------- ADMIN ANALYTICS ----------------
@app.route("/admin/analytics")
def admin_analytics():
    if session.get("role") != "admin":
        return redirect("/login")

    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT COUNT(*) FROM complaints")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM complaints WHERE status='Pending'")
    pending = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM complaints WHERE status='InProgress'")
    inprogress = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM complaints WHERE status='Solved'")
    solved = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE role='student'")
    students = cur.fetchone()[0]

    db.close()

    return render_template(
        "admin_analytics.html",
        total=total,
        pending=pending,
        inprogress=inprogress,
        solved=solved,
        students=students
    )



if __name__ == "__main__":
    app.run(debug=True)
