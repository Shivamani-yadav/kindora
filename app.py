from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3, os, random, smtplib
import razorpay
from werkzeug.utils import secure_filename
from email.message import EmailMessage

app = Flask(__name__)
app.secret_key = "your_secret_key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "database.db")
razorpay_client = razorpay.Client(auth=("YOUR_KEY_ID", "YOUR_KEY_SECRET"))

# ================= EMAIL CONFIG (SET YOURS) =================
SMTP_EMAIL = "nekuavasarama21@gmail.com"
SMTP_APP_PASSWORD = "clpnowhuqqjmhsdf"
SMTP_SERVER = "smtp.gmail.com" 
SMTP_PORT_SSL = 465

def send_email(to_email: str, subject: str, body_text: str, body_html: str = None):
    try:
        msg = EmailMessage()

        if body_html:
            msg.add_alternative(body_html, subtype="html")
        else:
            msg.set_content(body_text)

        msg["Subject"] = subject
        msg["From"] = SMTP_EMAIL
        msg["To"] = to_email

        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT_SSL)
        server.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
        server.send_message(msg)
        server.quit()

        print("Email sent successfully")

    except Exception as e:
        print("EMAIL ERROR:", e)
def safe_str(x):
    return "" if x is None else str(x)


def parse_food_details(message: str):
    """
    Your food message format in DB is like:
    "FoodName | Occasion: ... | Note: ... | Extras: ... | Date: YYYY-MM-DD"
    We extract:
      - item_name = FoodName
      - date = after "Date:"
    """
    msg = safe_str(message)
    item_name = msg.split("|")[0].strip() if msg else "-"
    date_val = "-"
    if "Date:" in msg:
        try:
            date_val = msg.split("Date:")[1].strip()
        except:
            date_val = "-"
    return item_name or "-", date_val or "-"


def parse_book_name(message: str):
    """
    Your book message format in DB is like:
    "Title | Author:..., Genre:..., Condition:..., Note:..."
    We extract only the Title.
    """
    msg = safe_str(message)
    book_name = msg.split("|")[0].strip() if msg else "-"
    return book_name or "-"


# ----------------- Initialize DB -----------------
def init_db():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # ---------------- Users Table ----------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            password TEXT
        )
    ''')

    # ---------------- Contributions Table ----------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contributions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            type TEXT,
            amount TEXT,
            quantity TEXT,
            message TEXT
        )
    ''')

    # Add status column safely for contributions
    try:
        cursor.execute("ALTER TABLE contributions ADD COLUMN status TEXT DEFAULT 'Pending'")
    except:
        pass

    # ---------------- Adoption Applications Table ----------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS adopt_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            full_name TEXT,
            age INTEGER,
            marital_status TEXT,
            spouse_type TEXT,
            income TEXT,
            address TEXT,
            num_children INTEGER,
            child1_gender TEXT,
            child2_gender TEXT,
            child3_gender TEXT,
            status TEXT DEFAULT 'Pending'
        )
    ''')

    # ✅ Option A: Add extra columns safely (Adoption)
    try:
        cursor.execute("ALTER TABLE adopt_applications ADD COLUMN marriage_years TEXT")
    except:
        pass

    try:
        cursor.execute("ALTER TABLE adopt_applications ADD COLUMN home_type TEXT")
    except:
        pass

    # ---------------- Children Table ----------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS children (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            user_name TEXT,
            phone TEXT,
            address TEXT,
            child_name TEXT,
            child_address TEXT,
            child_photo TEXT,
            status TEXT DEFAULT 'Pending'
        )
    ''')
    try:
        cursor.execute("ALTER TABLE children ADD COLUMN police_station_id TEXT")
    except:
        pass
    # ---------------- Matrimony Requests Table ----------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matrimony_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            user_name TEXT,
            user_gender TEXT,

            selected_profile_id INTEGER,
            selected_profile_name TEXT,
            selected_profile_age INTEGER,
            selected_profile_gender TEXT,
            selected_profile_occupation TEXT,
            selected_profile_address TEXT,

            status TEXT DEFAULT 'Pending'
        )
    ''')

    # ✅ Add profile image column safely (for modal image)
    try:
        cursor.execute("ALTER TABLE matrimony_requests ADD COLUMN selected_profile_image TEXT")
    except:
        pass
    # ---------------- Matrimony Profiles Table ----------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matrimony_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            age TEXT,
            gender TEXT,
            occupation TEXT,
            address TEXT,
            image TEXT
        
        )
    ''')
    conn.commit()
    conn.close()


# Run once at start (ONLY ONCE)
init_db()
# ----------------- Admin Credentials -----------------
admins = [
    "24h51a0526@cmrcet.ac.in",
    "24h51a05cb@cmrcet.ac.in",
    "24h51a05fy@cmrcet.ac.in",
    "24h51a05t0@cmrcet.ac.in",
    "24h51a05t2@cmrcet.ac.in",
    "25h55a0521@cmrcet.ac.in"
]
admin_password = "12306"

# Map email prefixes to names
admin_names = {
    "26": "Mounika",
    "cb": "Raghu Yadav",
    "fy": "Shivamani Yadav",
    "t0": "Indra",
    "t2": "Bhavana",
    "21": "Akshay"
}

# ----------------- Routes -----------------

# Home
@app.route("/")
def home():
    return render_template("index.html")


# User Register
@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        if cursor.fetchone():
            error = "Email already exists, please login"
        else:
            cursor.execute("INSERT INTO users (name,email,password) VALUES (?,?,?)",
                           (name, email, password))
            conn.commit()
            conn.close()
            return redirect("/login")
        conn.close()
    return render_template("register.html", error=error)


# User Login
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user:
            if user[3] == password:
                session["user_name"] = user[1]
                session["user_email"] = user[2]
                return redirect("/dashboard")
            else:
                error = "Incorrect password"
        else:
            error = "Email not found, please register"
    return render_template("login.html", error=error)


# Forgot Password
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    message = None
    if request.method == "POST":
        email = request.form["email"]

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user:
            otp = str(random.randint(100000, 999999))
            session["reset_otp"] = otp
            session["reset_email"] = email

            try:
                body = f"Your KINDORA password reset OTP is: {otp}"
                send_email(email, "KINDORA Password Reset OTP", body)
                return redirect("/verify-otp")
            except Exception as e:
                print("Failed to send email:", e)
                message = "Failed to send email. Try again."
        else:
            message = "Email not found!"
    return render_template("forgot_password.html", message=message)


# Verify OTP
@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    message = None
    if request.method == "POST":
        entered_otp = request.form["otp"]
        if entered_otp == session.get("reset_otp"):
            return redirect("/reset-password")
        else:
            message = "Invalid OTP!"
    return render_template("verify_otp.html", message=message)


# Reset Password
@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    message = None
    if request.method == "POST":
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        if new_password == confirm_password:
            email = session.get("reset_email")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET password=? WHERE email=?", (new_password, email))
            conn.commit()
            conn.close()

            session.pop("reset_otp", None)
            session.pop("reset_email", None)

            return redirect("/login")
        else:
            message = "Passwords do not match!"
    return render_template("reset_password.html", message=message)


# User Dashboard
@app.route("/dashboard")
def dashboard():
    if "user_name" not in session:
        return redirect("/login")
    return render_template("dashboard.html", name=session["user_name"], user_email=session["user_email"])


# Change Name
@app.route("/change-name", methods=["GET", "POST"])
def change_name():
    if "user_email" not in session:
        return redirect("/login")
    message = None
    if request.method == "POST":
        new_name = request.form["new_name"]
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET name=? WHERE email=?", (new_name, session["user_email"]))
        conn.commit()
        conn.close()
        session["user_name"] = new_name
        message = "Name updated successfully!"
    return render_template("change_name.html", message=message)


# Account Settings
@app.route("/account-settings", methods=["GET", "POST"])
def account_settings():
    if "user_email" not in session:
        return redirect("/login")
    message = None
    if request.method == "POST":
        action = request.form.get("action")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        if action == "change_name":
            new_name = request.form["new_name"]
            cursor.execute("UPDATE users SET name=? WHERE email=?", (new_name, session["user_email"]))
            conn.commit()
            session["user_name"] = new_name
            message = "Name updated successfully!"
        elif action == "change_password":
            current = request.form["current_password"]
            new = request.form["new_password"]
            confirm = request.form["confirm_password"]
            cursor.execute("SELECT password FROM users WHERE email=?", (session["user_email"],))
            user = cursor.fetchone()
            if user and user[0] == current:
                if new == confirm:
                    cursor.execute("UPDATE users SET password=? WHERE email=?", (new, session["user_email"]))
                    conn.commit()
                    message = "Password updated successfully!"
                else:
                    message = "New passwords do not match!"
            else:
                message = "Current password incorrect!"
        conn.close()
    return render_template("acc_setting.html", message=message)


# About
@app.route("/about")
def about():
    return render_template("about.html")


# ----------------- Admin Routes -----------------
@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    message = None
    if request.method == "POST":
        email = request.form.get("email").lower()
        password = request.form.get("password")

        session.pop("admin_email", None)

        if email not in admins:
            message = "Only admins can login"
        elif password != admin_password:
            message = "Incorrect password"
        else:
            session["admin_email"] = email
            return redirect("/admin-dashboard")

    return render_template("admin_login.html", message=message)


@app.route("/admin-dashboard")
def admin_dashboard():
    if "admin_email" not in session:
        return redirect("/admin-login")

    email = session["admin_email"]
    prefix = email[8:10].lower()
    name = admin_names.get(prefix, "Admin")

    return render_template("admin_dashboard.html", name=name, admin_email=email)


@app.route("/registered-child")
def registered_child():
    if "admin_email" not in session:
        return redirect("/admin-login")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, user_email, user_name, phone, address, child_name, child_address, child_photo, police_station_id, status
        FROM children
        ORDER BY CASE WHEN status='Pending' THEN 0 ELSE 1 END, id DESC
    """)
    children = cursor.fetchall()
    conn.close()

    return render_template("registered_child.html", children=children)


@app.route("/child-action", methods=["POST"])
def child_action():
    if "admin_email" not in session:
        return redirect("/admin-login")

    child_id = request.form["child_id"]
    action = request.form["action"]  # 'approve' or 'cancel'

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE children SET status=? WHERE id=?", (action.capitalize(), child_id))
    conn.commit()

    cursor.execute("SELECT user_email, child_name FROM children WHERE id=?", (child_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        user_email, child_name = row
        try:
            subject = f"KINDORA Child Submission {action.capitalize()}"
            body = f"Hello,\n\nYour child '{child_name}' has been {action.capitalize()} by KINDORA team.\n\nThank you!"
            send_email(user_email, subject, body)
        except Exception as e:
            print("Email sending failed:", e)

    return redirect("/registered-child")
@app.route("/child-approve-all", methods=["POST"])
def child_approve_all():
    if "admin_email" not in session:
        return redirect("/admin-login")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # get all pending children first for email
    cursor.execute("""
        SELECT id, user_email, child_name
        FROM children
        WHERE IFNULL(status, 'Pending') = 'Pending'
        ORDER BY id DESC
    """)
    pending_children = cursor.fetchall()

    # approve all pending children
    cursor.execute("""
        UPDATE children
        SET status='Approved'
        WHERE IFNULL(status, 'Pending')='Pending'
    """)
    conn.commit()
    conn.close()

    # send email to all approved users
    for child in pending_children:
        child_id, user_email, child_name = child
        try:
            subject = "KINDORA Child Submission Approved"
            body = f"""Hello,

Your child submission '{child_name}' has been Approved by KINDORA team.

Thank you!
"""
            send_email(user_email, subject, body)
        except Exception as e:
            print(f"Approve-all email failed for child ID {child_id}:", e)

    return redirect("/registered-child")

@app.route("/admin-logout")
def admin_logout():
    session.pop("admin_email", None)
    return redirect("/admin-login")


@app.route("/register-child", methods=["GET", "POST"])
def register_a_child():
    if "user_name" not in session:
        return redirect("/login")

    confirmation = None
    email_sent = False
    child_id = None

    if request.method == "POST":
        user_name = session.get("user_name", "")
        user_email = session.get("user_email", "")
        police_station_id = request.form.get("police_station_id", "")
        phone = request.form.get("phone", "")
        address = request.form.get("police_station_name", "")
        child_name = request.form.get("child_name", "")
        child_address = request.form.get("child_found_address", "")
        child_photo = request.files.get("child_photo")

        upload_folder = os.path.join(BASE_DIR, "static/uploads")
        os.makedirs(upload_folder, exist_ok=True)

        photo_path = ""
        if child_photo and child_photo.filename:
            photo_filename = secure_filename(child_photo.filename)
            child_photo.save(os.path.join(upload_folder, photo_filename))
            photo_path = photo_filename

        child_id = f"KID{random.randint(1000,9999)}"

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO children (
                    user_email, user_name, phone, address,
                    child_name, child_address, child_photo,
                    police_station_id, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_email, user_name, phone, address,
                child_name, child_address, photo_path,
                police_station_id, "Pending"
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print("Database insertion failed:", e)

        try:
            if user_email:
                send_email(
                    user_email,
                    "KINDORA Child Registration Confirmation",
                    f"Hey {user_name}, your child registration was submitted successfully."
                )
                email_sent = True
        except Exception as e:
            print("Email sending failed:", e)

        confirmation = f"Child registration submitted! Child: {child_name}, Found at: {child_address}"

    return render_template(
        "register_a_child.html",
        user_name=session.get("user_name", ""),
        confirmation=confirmation,
        email_sent=email_sent,
        child_id=child_id
    )
@app.route("/child-delete", methods=["POST"])
def child_delete():
    if "admin_email" not in session:
        return redirect("/admin-login")
    child_id = request.form["child_id"]
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM children WHERE id=?", (child_id,))
    conn.commit()
    conn.close()
    return redirect("/registered-child")


@app.route("/view-child/<int:child_id>")
def view_child(child_id):
    if "admin_email" not in session:
        return redirect("/admin-login")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_name, user_email, phone, address, child_name, child_address, child_photo, status
        FROM children
        WHERE id=?
    """, (child_id,))
    child = cursor.fetchone()
    conn.close()

    if not child:
        return "Child not found", 404

    return render_template("view_child.html", child=child)


# ================== CONTRIBUTIONS ADMIN PAGE ==================
@app.route("/contributed")
def contributed():
    if "admin_email" not in session:
        return redirect("/admin-login")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            c.id,
            IFNULL(u.name, '-') as user_name,
            c.user_email,
            c.type,
            c.amount,
            c.quantity,
            c.message,
            IFNULL(c.status, 'Recieved') as status
        FROM contributions c
        LEFT JOIN users u ON u.email = c.user_email
        
        ORDER BY
            CASE WHEN IFNULL(c.status,'Pending')='Pending' THEN 0 ELSE 1 END,
            c.id DESC
    """)
    contributions = cursor.fetchall()
    conn.close()

    return render_template("contributed.html", contributions=contributions)


# ✅ UPDATED: Approve/Cancel + Send Email (Food: items+date, Books: only book name)
@app.route("/contribution-action", methods=["POST"])
def contribution_action():
    if "admin_email" not in session:
        return redirect("/admin-login")

    contribution_id = request.form["contribution_id"]
    action = request.form["action"]  # 'Approved' or 'Cancelled'

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Fetch details for email
    cursor.execute("""
        SELECT 
            IFNULL(u.name, '-') as user_name,
            c.user_email,
            c.type,
            IFNULL(c.amount,'') as amount,
            IFNULL(c.quantity,'') as quantity,
            IFNULL(c.message,'') as message
        FROM contributions c
        LEFT JOIN users u ON u.email = c.user_email
        WHERE c.id=?
    """, (contribution_id,))
    row = cursor.fetchone()

    # Update status
    cursor.execute("UPDATE contributions SET status=? WHERE id=?", (action, contribution_id))
    conn.commit()
    conn.close()

    # Send email after update
    if row:
        user_name, user_email, ctype, amount, quantity, message = row
        ctype_l = safe_str(ctype).strip().lower()

        try:
            if action == "Approved":
                subject = "KINDORA Contribution Approved ✅"

                if ctype_l == "food":
                    food_item, food_date = parse_food_details(message)
                    body = f"""Hello {user_name},

Your Food contribution has been APPROVED ✅

Food Item: {food_item}
Date: {food_date}

Thank you for supporting KINDORA 💛
- Team KINDORA
"""
                    send_email(user_email, subject, body)

                elif ctype_l in ["book", "books"]:
                    book_name = parse_book_name(message)
                    subject = "KINDORA Books Contribution Approved ✅"
                    body = f"""Hello {user_name},

Your Books contribution has been APPROVED ✅

Book Name: {book_name}

Thank you for supporting KINDORA 💛
- Team KINDORA
"""
                    send_email(user_email, subject, body)

                else:
                    body = f"""Hello {user_name},

Your contribution has been APPROVED ✅

Type: {ctype}
Details: {amount or quantity}

Thank you for supporting KINDORA 💛
- Team KINDORA
"""
                    send_email(user_email, subject, body)

            else:  # Cancelled
                subject = "KINDORA Contribution Cancelled ❌"

                # Food/Books still okay with short message
                body = f"""Hello {user_name},

Your contribution has been CANCELLED ❌

Type: {ctype}

If you have any questions, please contact the admin team.

- Team KINDORA
"""
                send_email(user_email, subject, body)

        except Exception as e:
            print("Contribution status email failed:", e)

    return redirect("/contributed")


@app.route("/contribution-delete", methods=["POST"])
def contribution_delete():
    if "admin_email" not in session:
        return redirect("/admin-login")

    contribution_id = request.form["contribution_id"]

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT IFNULL(status,'Pending') FROM contributions WHERE id=?", (contribution_id,))
    row = cursor.fetchone()
    if row and row[0] != "Pending":
        cursor.execute("DELETE FROM contributions WHERE id=?", (contribution_id,))
        conn.commit()

    conn.close()
    return redirect("/contributed")
@app.route("/approve-all", methods=["POST"])
def approve_all():
    if "admin_email" not in session:
        return redirect("/admin-login")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1) Get all pending contributions first (so we can email them)
    cursor.execute("""
        SELECT c.id,
               IFNULL(u.name,'-') as user_name,
               c.user_email,
               c.type,
               IFNULL(c.amount,'') as amount,
               IFNULL(c.quantity,'') as quantity,
               IFNULL(c.message,'') as message
        FROM contributions c
        LEFT JOIN users u ON u.email = c.user_email
        WHERE IFNULL(c.status,'Pending')='Pending'
        ORDER BY c.id DESC
    """)
    pending_rows = cursor.fetchall()

    # 2) Approve all pending in DB
    cursor.execute("""
        UPDATE contributions
        SET status='Approved'
        WHERE IFNULL(status,'Pending')='Pending'
    """)
    conn.commit()
    conn.close()

    # 3) Send emails one by one
    for (cid, user_name, user_email, ctype, amount, quantity, message) in pending_rows:
        try:
            ctype_l = (ctype or "").strip().lower()

            if ctype_l == "food":
                # message example: "Biryani | Occasion: ... | Note: ... | Extras: ... | Date: 2026-02-25"
                msg = message or ""
                food_item = msg.split("|")[0].strip() if msg else "-"
                food_date = "-"
                if "Date:" in msg:
                    food_date = msg.split("Date:")[1].strip()

                subject = "KINDORA Food Contribution Approved ✅"
                body = f"""Hello {user_name},

Your Food contribution has been APPROVED ✅

Food Item: {food_item}
Date: {food_date}

- Team KINDORA
"""
                send_email(user_email, subject, body)

            elif ctype_l in ["book", "books"]:
                # message example: "Atomic Habits | Author:... | Genre:..."
                msg = message or ""
                book_name = msg.split("|")[0].strip() if msg else "-"

                subject = "KINDORA Books Contribution Approved ✅"
                body = f"""Hello {user_name},

Your Books contribution has been APPROVED ✅

Book Name: {book_name}

- Team KINDORA
"""
                send_email(user_email, subject, body)

            else:
                subject = "KINDORA Contribution Approved ✅"
                body = f"""Hello {user_name},

Your contribution has been APPROVED ✅

Type: {ctype}
Details: {amount or quantity}

- Team KINDORA
"""
                send_email(user_email, subject, body)

        except Exception as e:
            print(f"Approve-all email failed for ID {cid}:", e)

    return redirect("/contributed")
@app.route("/adopted")
def adopted():
    if "admin_email" not in session:
        return redirect("/admin-login")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, user_email, full_name, age, marital_status, spouse_type, income, address,
               num_children, child1_gender, child2_gender, child3_gender,
               IFNULL(status,'Pending') as status
        FROM adopt_applications
        ORDER BY CASE WHEN IFNULL(status,'Pending')='Pending' THEN 0 ELSE 1 END, id DESC
    """)
    applications = cursor.fetchall()
    conn.close()

    return render_template("adopted.html", applications=applications)
@app.route("/adopt-action", methods=["POST"])
def adopt_action():
    if "admin_email" not in session:
        return redirect("/admin-login")

    application_id = request.form["application_id"]
    action = request.form["action"]  # Approved / Cancelled

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE adopt_applications SET status=? WHERE id=?", (action, application_id))
    conn.commit()
    conn.close()

    return redirect("/adopted")
@app.route("/adopt-approve-all", methods=["POST"])
def adopt_approve_all():
    if "admin_email" not in session:
        return redirect("/admin-login")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE adopt_applications
        SET status='Approved'
        WHERE IFNULL(status,'Pending')='Pending'
    """)
    conn.commit()
    conn.close()

    return redirect("/adopted")
@app.route("/adopt-delete", methods=["POST"])
def adopt_delete():
    if "admin_email" not in session:
        return redirect("/admin-login")

    application_id = request.form["application_id"]

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT IFNULL(status,'Pending') FROM adopt_applications WHERE id=?", (application_id,))
    row = cursor.fetchone()

    if row and row[0] != "Pending":
        cursor.execute("DELETE FROM adopt_applications WHERE id=?", (application_id,))
        conn.commit()

    conn.close()
    return redirect("/adopted")
@app.route("/matrimony-requests")
def matrimony_requests():
    if "admin_email" not in session:
        return redirect("/admin-login")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
       SELECT id, user_name, user_email, user_gender,
              selected_profile_name, selected_profile_age, selected_profile_gender,
              selected_profile_occupation, selected_profile_address,
              selected_profile_image,
              IFNULL(status,'Pending') as status
       FROM matrimony_requests
       ORDER BY CASE WHEN IFNULL(status,'Pending')='Pending' THEN 0 ELSE 1 END, id DESC
    """)

    requests_data = cursor.fetchall()
    conn.close()

    return render_template("matrimony_requests.html", requests_data=requests_data)


@app.route("/matrimony-action", methods=["POST"])
def matrimony_action():
    if "admin_email" not in session:
        return redirect("/admin-login")

    req_id = request.form.get("request_id")
    action = request.form.get("action")  # "Approved" / "Cancelled"

    if not req_id or action not in ["Approved", "Cancelled"]:
        return redirect("/matrimony-requests")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Fetch request details (for optional email)
    cursor.execute("""
        SELECT user_email, user_name, selected_profile_name
        FROM matrimony_requests
        WHERE id=?
    """, (req_id,))
    req = cursor.fetchone()

    # Update status
    cursor.execute("UPDATE matrimony_requests SET status=? WHERE id=?", (action, req_id))
    conn.commit()
    conn.close()

    # ✅ OPTIONAL: send email to user on approve/cancel (remove if you don't want)
    try:
        if req:
            user_email = req["user_email"]
            user_name = req["user_name"] or "User"
            profile_name = req["selected_profile_name"] or "the selected profile"

            if action == "Approved":
                subject = "KINDORA Matrimony - Request Approved ✅"
                html_content = f"""
                <html>
                  <body style="font-family: Arial; color:#333;">
                    <p>Hi {user_name},</p>
                    <p>Your matrimony request has been <b>APPROVED</b>.</p>
                    <p><b>Selected Profile:</b> {profile_name}</p>
                    <p>💛 - Team KINDORA</p>
                  </body>
                </html>
                """
            else:
                subject = "KINDORA Matrimony - Request Cancelled ❌"
                html_content = f"""
                <html>
                  <body style="font-family: Arial; color:#333;">
                    <p>Hi {user_name},</p>
                    <p>Your matrimony request has been <b>CANCELLED</b>.</p>
                    <p><b>Selected Profile:</b> {profile_name}</p>
                    <p>If you think this is a mistake, please contact support.</p>
                    <p>💛 - Team KINDORA</p>
                  </body>
                </html>
                """

            send_email(user_email, subject, "", body_html=html_content)
    except Exception as e:
        print("Approval email failed:", e)

    return redirect("/matrimony-requests")


@app.route("/matrimony-approve-all", methods=["POST"])
def matrimony_approve_all():
    if "admin_email" not in session:
        return redirect("/admin-login")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # ✅ OPTIONAL: fetch all pending first (for optional email)
    cursor.execute("""
        SELECT id, user_email, user_name, selected_profile_name
        FROM matrimony_requests
        WHERE IFNULL(status,'Pending')='Pending'
    """)
    pending = cursor.fetchall()

    cursor.execute("""
        UPDATE matrimony_requests
        SET status='Approved'
        WHERE IFNULL(status,'Pending')='Pending'
    """)
    conn.commit()
    conn.close()

    # ✅ OPTIONAL: send email to all approved users (remove if you don't want)
    try:
        for req in pending:
            user_email = req["user_email"]
            user_name = req["user_name"] or "User"
            profile_name = req["selected_profile_name"] or "the selected profile"

            subject = "KINDORA Matrimony - Request Approved ✅"
            html_content = f"""
            <html>
              <body style="font-family: Arial; color:#333;">
                <p>Hi {user_name},</p>
                <p>Your matrimony request has been <b>APPROVED</b>.</p>
                <p><b>Selected Profile:</b> {profile_name}</p>
                <p>💛 - Team KINDORA</p>
              </body>
            </html>
            """
            send_email(user_email, subject, "", body_html=html_content)
    except Exception as e:
        print("Approve-all email failed:", e)

    return redirect("/matrimony-requests")
# ================== Matrimony Profiles add ==================
@app.route("/add-matrimony-profile", methods=["GET", "POST"])
def add_matrimony_profile():
    if "admin_email" not in session:
        return redirect("/admin-login")

    os.makedirs("static/matrimony_profiles", exist_ok=True)

    if request.method == "POST":
        name = request.form.get("name")
        age = request.form.get("age")
        gender = request.form.get("gender")
        occupation = request.form.get("occupation")
        address = request.form.get("address")

        image = request.files.get("image")
        image_path = ""

        if image and image.filename != "":
            filename = secure_filename(image.filename)
            save_path = os.path.join("static/matrimony_profiles", filename)
            image.save(save_path)
            image_path = "/" + save_path.replace("\\", "/")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO matrimony_profiles
            (name, age, gender, occupation, address, image)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, age, gender, occupation, address, image_path))

        conn.commit()
        conn.close()

        return redirect("/add-matrimony-profile")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, age, gender, occupation, address, image
        FROM matrimony_profiles
        ORDER BY id DESC
    """)
    profiles = cursor.fetchall()
    conn.close()

    return render_template("add_delete.html", profiles=profiles)
# ================== Matrimony delete Profiles ==================
@app.route("/delete-matrimony-profile", methods=["POST"])
def delete_matrimony_profile():
    if "admin_email" not in session:
        return redirect("/admin-login")

    profile_id = request.form.get("profile_id")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM matrimony_profiles WHERE id=?", (profile_id,))
    conn.commit()
    conn.close()

    return redirect("/add-matrimony-profile")
# ================== USER CONTRIBUTIONS ==================
@app.route("/contribute")
def contribute():
    if "user_name" not in session:
        return redirect("/login")
    return render_template("contribute.html")


@app.route("/money", methods=["GET", "POST"])
def money():
    message = None

    if request.method == "POST":
        amount = request.form["amount"]
        note = request.form["message"]
        user_email = session.get("user_email")
        user_name = session.get("user_name")

        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO contributions (user_email, type, amount, quantity, message) VALUES (?, ?, ?, ?, ?)",
            (user_email, "Money", amount, "-", note)
        )
        conn.commit()
        conn.close()

        try:
            transaction_id = f"TXN{random.randint(100000,999999)}"
            subject = "KINDORA Donation Confirmation"
            body = f"""
Hello {user_name},

Thank you for donating ₹{amount} to KINDORA ❤️

Transaction Details:
Transaction ID: {transaction_id}
Amount: ₹{amount}
Message: {note}

Thank you for your generosity!
- Team KINDORA
"""
            send_email(user_email, subject, body)
        except Exception as e:
            print("Email sending failed:", e)

        message = f"Payment of ₹{amount} Successful! Thank you for donating."

    return render_template("money.html", message=message)


@app.route("/donate/books", methods=["GET", "POST"])
def donate_books():
    if "user_email" not in session:
        return redirect("/login")

    message = None
    donated_books = []

    if request.method == "POST":
        user_name = session["user_name"]
        user_email = session["user_email"]

        titles = request.form.getlist("title[]")
        authors = request.form.getlist("author[]")
        genres = request.form.getlist("genre[]")
        conditions = request.form.getlist("condition[]")
        quantities = request.form.getlist("quantity[]")
        notes = request.form.getlist("message[]")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        for i in range(len(titles)):
            note_text = f"Author: {authors[i]}, Genre: {genres[i]}, Condition: {conditions[i]}, Note: {notes[i]}"
            cursor.execute(
                "INSERT INTO contributions (user_email, type, amount, quantity, message) VALUES (?, ?, ?, ?, ?)",
                (user_email, "Book", "-", quantities[i], f"{titles[i]} | {note_text}")
            )
            donated_books.append(f"{titles[i]} | {note_text} | Quantity: {quantities[i]}")
        conn.commit()
        conn.close()
        message = "Books donation submitted successfully!"

        try:
            import html
            book_list_html = "<br>".join(html.escape(b) for b in donated_books)
            html_content = f"""
<html>
  <body style="font-family: Arial, sans-serif; color: #333; background-color: #ffffff; padding: 20px;">
    <p style="font-size:24px; font-weight:bold; margin-bottom:20px; color:#111;">
      Thank you for your donation, {html.escape(user_name)}!
    </p>
    <p style="font-size:16px; margin-bottom:10px;">You have donated the following books:</p>
    <p style="font-size:16px; line-height:1.6;">
      {book_list_html}
    </p>
    <p style="font-size:16px; margin-top:20px;">
      Your contribution is greatly appreciated! 💛
    </p>
    <p style="font-size:14px; color:#555;">- Team KINDORA</p>
  </body>
</html>
"""
            send_email(user_email, "KINDORA Book Donation Confirmation", "", body_html=html_content)
        except Exception as e:
            print("Email sending failed:", e)

    return render_template("donation.html", item="Books", message=message, donated_books=donated_books)


@app.route("/donate/food", methods=["GET", "POST"])
def donate_food():
    if "user_email" not in session:
        return redirect("/login")

    message = None

    if request.method == "POST":
        user_name = session["user_name"]
        user_email = session["user_email"]

        food_names = request.form.getlist("food_name[]")
        quantities = request.form.getlist("quantity[]")
        units = request.form.getlist("unit[]")
        food_types = request.form.getlist("food_type[]")
        occasions = request.form.getlist("occasion[]")
        messages = request.form.getlist("message[]")
        donation_dates = request.form.getlist("donation_date[]")
        extra_items = request.form.getlist("extra_item[]")
        extra_quantities = request.form.getlist("extra_quantity[]")

        food_list = []
        for i in range(len(food_names)):
            extras_text = ""
            for j, item in enumerate(extra_items):
                if extra_quantities[j]:
                    extras_text += f"{item} x {extra_quantities[j]}, "
            extras_text = extras_text.rstrip(", ")

            food_list.append(
                f"{food_names[i]} ({quantities[i]} {units[i]}, {food_types[i]}, "
                f"Occasion: {occasions[i] or 'N/A'}, Note: {messages[i] or 'N/A'}, Date: {donation_dates[i]}"
                f"{', Extras: ' + extras_text if extras_text else ''})"
            )

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO contributions (user_email, type, amount, quantity, message) VALUES (?, ?, ?, ?, ?)",
                (
                    user_email,
                    "Food",
                    f"{quantities[i]} {units[i]}",
                    food_types[i],
                    f"{food_names[i]} | Occasion: {occasions[i]} | Note: {messages[i]} | Extras: {extras_text} | Date: {donation_dates[i]}"
                )
            )
            conn.commit()
            conn.close()

        try:
            import html
            food_html = "<br>".join(html.escape(f) for f in food_list)
            html_content = f"""
<html>
  <body style="font-family: Arial; color: #333;">
    <p>Hi {html.escape(user_name)},</p>
    <p>Thank you for your food donation! Here are the details of your donation:</p>
    <p>{food_html}</p>
    <p>Your contribution is greatly appreciated! 💛</p>
    <p>- Team KINDORA</p>
  </body>
</html>
"""
            send_email(user_email, "KINDORA Food Donation Confirmation", "", body_html=html_content)
        except Exception as e:
            print("Email sending failed:", e)

        message = "Your food donation has been successfully submitted! A confirmation email has been sent."

    return render_template("food.html", message=message)


# Adopt Page
@app.route("/adopt-options")
def adopt_options():
    return render_template("adopt_options.html")


@app.route("/adopt-child", methods=["GET", "POST"])
def adopt():
    if request.method == "POST":
        full_name = request.form.get("full_name")
        age = request.form.get("age")
        marital_status = request.form.get("marital_status")
        spouse_type = request.form.get("spouse_type")
        marriage_years = request.form.get("marriage_years")
        income = request.form.get("income")
        home_type = request.form.get("home_type")
        address = request.form.get("address")
        has_children = request.form.get("has_children")
        children_count = int(request.form.get("children_count") or 0)

        # collect up to 3 child genders (safely)
        children_genders = []
        for i in range(children_count):
            if i >= 3:
                break
            children_genders.append(request.form.get(f"child_gender_{i+1}") or "")

        # pad to exactly 3 for DB columns
        child1_gender = children_genders[0] if len(children_genders) > 0 else ""
        child2_gender = children_genders[1] if len(children_genders) > 1 else ""
        child3_gender = children_genders[2] if len(children_genders) > 2 else ""

        user_email = session.get("user_email")
        user_name = session.get("user_name")

        # keep the session copy (so user sees confirmation page exactly as before)
        session['applicant'] = {
            "full_name": full_name,
            "age": age,
            "marital_status": marital_status,
            "spouse_type": spouse_type,
            "marriage_years": marriage_years,
            "income": income,
            "home_type": home_type,
            "address": address,
            "has_children": has_children,
            "children_count": children_count,
            "children_genders": children_genders
        }

        # --- INSERT into DB so admin can see it in /adopted ---
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO adopt_applications
                (user_email, full_name, age, marital_status, spouse_type, marriage_years,
                 income, home_type, address, num_children, child1_gender, child2_gender, child3_gender, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
            """, (
                user_email, full_name, age, marital_status, spouse_type, marriage_years,
                income, home_type, address, children_count, child1_gender, child2_gender, child3_gender
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            # log error but continue so user still gets confirmation
            print("Adoption insertion failed:", e)

        # --- Send confirmation email (keeps existing behavior) ---
        try:
            import html
            children_details_html = ""
            if has_children == "Yes" and children_count > 0:
                children_details_html = "<br><strong>Children Details:</strong><br>"
                for i, gender in enumerate(children_genders):
                    children_details_html += f"Child {i+1}: {html.escape(str(gender))}<br>"

            html_content = f"""
            <html>
              <body style="font-family: Arial, sans-serif; color: #333;">
                <p>Hi {html.escape(user_name)},</p>
                <p>Thank you for submitting your adoption application! Here are your submitted details:</p>
                <p>
                    <strong>Applicant Details:</strong><br>
                    Name: {html.escape(full_name)}<br>
                    Age: {html.escape(age)}<br>
                    Marital Status: {html.escape(marital_status)}<br>
                    Spouse Type: {html.escape(spouse_type)}<br>
                    Years of Marriage: {html.escape(marriage_years)}</br>
                    Income: {html.escape(income)}<br>
                    Home Type: {html.escape(home_type)}<br>
                    Address: {html.escape(address)}<br>
                    {children_details_html}
                </p>
                <p>Our team will review your application and contact you via your registered email.</p>
                <p>💛 - Team KINDORA</p>
              </body>
            </html>
            """
            send_email(user_email, "KINDORA Adoption Application Confirmation", "", body_html=html_content)
        except Exception as e:
            print("Email sending failed:", e)

        return redirect("/adopt-child?submitted=1")

    submitted = request.args.get("submitted") == "1"
    applicant = session.pop("applicant", None) if submitted else None

    return render_template("adopt_child.html", submitted=submitted, applicant=applicant)


# Matrimony page (kept as-is from your file)
@app.route("/matrimony", methods=["GET", "POST"])
def matrimony():
    edit_mode = request.args.get("edit") == "1"

    if "form_data" not in session:
        session["form_data"] = {
            'name': '',
            'age': '',
            'address': '',
            'occupation': '',
            'height': '',
            'weight': '',
            'income': '',
            'residence_type': '',
            'family_status': '',
            'gender': ''
        }

    # ✅ ADD THIS BLOCK (FIRST OPEN SHOULD SHOW FORM)
    # If user opens /matrimony directly (fresh start), show registration form
    if (request.method == "GET"
        and request.args.get("submitted") is None
        and request.args.get("view") is None
        and not edit_mode):
        session["submitted"] = False
        # optional: clear old form values also (uncomment if you want blank form always)
        # session["form_data"] = {
        #     'name': '', 'age': '', 'address': '', 'occupation': '',
        #     'height': '', 'weight': '', 'income': '',
        #     'residence_type': '', 'family_status': '', 'gender': ''
        # }
        session.modified = True

    # -------------------- FORM SUBMIT (user details) --------------------
    if request.method == "POST" and "select_profile_id" not in request.form:
        session["form_data"] = {
            'name': request.form.get('name', ''),
            'age': request.form.get('age', ''),
            'address': request.form.get('address', ''),
            'occupation': request.form.get('occupation', ''),
            'height': request.form.get('height', ''),
            'weight': request.form.get('weight', ''),
            'income': request.form.get('income', ''),
            'residence_type': request.form.get('residence_type', ''),
            'family_status': request.form.get('family_status', ''),
            'gender': request.form.get('gender', '')
        }
        session["submitted"] = True
        session.modified = True
        return redirect("/matrimony?submitted=1")

    # submitted flag from URL
    if request.args.get("submitted") == "1":
        session["submitted"] = True

    # -------------------- Form data for editing --------------------
    form_data_for_form = session["form_data"] if edit_mode else {
        'name': '',
        'age': '',
        'address': '',
        'occupation': '',
        'height': '',
        'weight': '',
        'income': '',
        'residence_type': '',
        'family_status': '',
        'gender': ''
    }

    # -------------------- Profiles --------------------
     # -------------------- Fixed Profiles --------------------
    profiles = [
        {"id": 1, "name": "Ram", "age": 25, "gender": "Male", "occupation": "Software Engineer", "address": "Hyderabad",
         "date_joined": "2024-01-01", "img": "/static/boy1.jpg"},
        {"id": 2, "name": "Rohan", "age": 28, "gender": "Male", "occupation": "Doctor", "address": "Mumbai",
         "date_joined": "2024-01-02", "img": "/static/boy2.jpg"},
        {"id": 3, "name": "Sita", "age": 27, "gender": "Female", "occupation": "Teacher", "address": "Delhi",
         "date_joined": "2024-01-03", "img": "/static/girl1.jpg"},
        {"id": 4, "name": "Ravi", "age": 30, "gender": "Male", "occupation": "Engineer", "address": "Bangalore",
         "date_joined": "2024-01-04", "img": "/static/boy3.jpg"},
        {"id": 5, "name": "Priya", "age": 26, "gender": "Female", "occupation": "Designer", "address": "Chennai",
         "date_joined": "2024-01-05", "img": "/static/girl2.jpg"},
        {"id": 6, "name": "Sneha", "age": 24, "gender": "Female", "occupation": "Artist", "address": "Kolkata",
         "date_joined": "2024-01-06", "img": "/static/girl3.jpg"}
    ]

    # -------------------- DB Profiles --------------------
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, age, gender, occupation, address, image
        FROM matrimony_profiles
        ORDER BY id DESC
    """)
    db_profiles = cursor.fetchall()
    conn.close()

    # add DB profiles after fixed profiles
    next_id = 1000
    for p in db_profiles:
        profiles.append({
            "id": next_id,
            "db_id": p["id"],
            "name": p["name"],
            "age": p["age"],
            "gender": p["gender"],
            "occupation": p["occupation"],
            "address": p["address"],
            "date_joined": "",
            "img": p["image"]
        })
        next_id += 1
    # Filter opposite gender
    user_gender = session.get("form_data", {}).get("gender", "")
    if user_gender == "Male":
        profiles = [p for p in profiles if p["gender"] == "Female"]
    elif user_gender == "Female":
        profiles = [p for p in profiles if p["gender"] == "Male"]

    confirmed_profile_id = None

    # -------------------- SELECT PROFILE (POST) --------------------
    if request.method == "POST" and "select_profile_id" in request.form:
        confirmed_profile_id = int(request.form["select_profile_id"])

        try:
            import html
            user_name = session.get("user_name")
            user_email = session.get("user_email")

            profile = next((p for p in profiles if p["id"] == confirmed_profile_id), None)
            if profile:

                # ✅ Save matrimony selection for admin approval (WITH IMAGE)
                try:
                    if "user_email" not in session:
                        return redirect("/login")

                    user_gender_db = session.get("form_data", {}).get("gender", "")

                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()

                    cursor.execute("""
                        SELECT id FROM matrimony_requests
                        WHERE user_email=? AND IFNULL(status,'Pending')='Pending'
                        ORDER BY id DESC LIMIT 1
                    """, (user_email,))
                    existing = cursor.fetchone()

                    if not existing:
                        cursor.execute("""
                            INSERT INTO matrimony_requests
                            (user_email, user_name, user_gender,
                             selected_profile_id, selected_profile_name, selected_profile_age,
                             selected_profile_gender, selected_profile_occupation, selected_profile_address,
                             selected_profile_image,
                             status)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
                        """, (
                            user_email, user_name, user_gender_db,
                            profile["id"], profile["name"], profile["age"],
                            profile["gender"], profile["occupation"], profile["address"],
                            profile["img"]
                        ))
                        conn.commit()

                    conn.close()

                except Exception as e:
                    print("Matrimony insertion failed:", e)

                # Existing email code
                profile_html = f"""
                <strong>Selected Profile Details:</strong><br>
                Name: {html.escape(profile['name'])}<br>
                Age: {profile['age']}<br>
                Occupation: {html.escape(profile['occupation'])}<br>
                Address: {html.escape(profile['address'])}<br>
                """

                html_content = f"""
                <html>
                  <body style="font-family: Arial; color:#333;">
                    <p>Hi {html.escape(user_name)},</p>
                    <p>Thank you for selecting a partner on KINDORA Matrimony. Here are the details of the profile you selected:</p>
                    <p>{profile_html}</p>
                    <p>Our team will review your application and contact you via your registered email.</p>
                    <p>💛 - Team KINDORA</p>
                  </body>
                </html>
                """
                send_email(user_email, "KINDORA Matrimony Profile Confirmation", "", body_html=html_content)

        except Exception as e:
            print("Email sending failed:", e)

    # -------------------- VIEW PROFILE (GET ?view=ID) --------------------
    view_profile_id = request.args.get("view")
    view_profile = None
    if view_profile_id:
        try:
            view_profile = next((p for p in profiles if p["id"] == int(view_profile_id)), None)
            # ✅ Force submitted true so view section renders properly
            session["submitted"] = True
        except:
            view_profile = None

    return render_template(
        "matrimony.html",
        form_data=form_data_for_form,
        submitted=session.get("submitted", False),
        edit_mode=edit_mode,
        profiles=profiles,
        view_profile=view_profile,
        confirmed_profile_id=confirmed_profile_id
    )
@app.route("/donate/items", methods=["GET", "POST"])
def donate_items():
    if "user_email" not in session:
        return redirect("/login")

    message = None

    if request.method == "POST":
        user_name = session["user_name"]
        user_email = session["user_email"]

        pickup_date = request.form.get("pickup_date")
        pickup_address = request.form.get("pickup_address")

        item_names = request.form.getlist("item_name[]")
        item_types = request.form.getlist("item_type[]")
        quantities = request.form.getlist("quantity[]")
        conditions = request.form.getlist("condition[]")
        messages = request.form.getlist("message[]")

        donated_items = []

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        for i in range(len(item_names)):
            full_message = (
                f"{item_names[i]} | "
                f"Type: {item_types[i]} | "
                f"Condition: {conditions[i]} | "
                f"Note: {messages[i]} | "
                f"Pickup Date: {pickup_date} | "
                f"Pickup Address: {pickup_address}"
            )

            cursor.execute(
                "INSERT INTO contributions (user_email, type, amount, quantity, message) VALUES (?, ?, ?, ?, ?)",
                (
                    user_email,
                    "Items",
                    "-",
                    quantities[i],
                    full_message
                )
            )

            donated_items.append(
                f"{item_names[i]} ({item_types[i]}) - Qty: {quantities[i]}, Condition: {conditions[i]}"
            )

        conn.commit()
        conn.close()

        try:
            subject = "KINDORA Donation Confirmation"

            item_details = "\n".join([f"{idx+1}. {item}" for idx, item in enumerate(donated_items)])

            body = f"""Hello {user_name},

Thank you for your generous contribution to KINDORA ❤️

We have successfully received your donation request.

Donation Details
--------------------------------
Items Donated:
{item_details}

Pickup Date: {pickup_date}
Pickup Address: {pickup_address}

What Happens Next?
--------------------------------
• Our KINDORA team will review your donation request.
• Our pickup team may contact you if needed.
• Your donation will help children supported by KINDORA.

Warm regards,
KINDORA Team
"""
            send_email(user_email, subject, body)
        except Exception as e:
            print("Email sending failed:", e)

        message = "success"

    return render_template("items.html", message=message)
@app.route("/donor")
def donor():
    return "<h1>Donor Page Coming Soon</h1>"


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)