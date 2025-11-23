from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import sqlite3, os
from werkzeug.utils import secure_filename
import smtplib, ssl
import psycopg2
from urllib.parse import urlparse
import psycopg2.extras # Thư viện cần thiết cho DictCursor

app = Flask(__name__)
app.secret_key = "secret123"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ----------------------------------------------------------------------
# HÀM KẾT NỐI DATABASE CHUNG
# ----------------------------------------------------------------------

def get_db():
    db_url = os.environ.get('DATABASE_URL')
    
    if db_url:
        # === KẾT NỐI VỚI POSTGRESQL (Môi trường Render) ===
        try:
            result = urlparse(db_url)
            conn = psycopg2.connect(
                database=result.path[1:],
                user=result.username,
                password=result.password,
                host=result.hostname,
                port=result.port
            )
            return conn
            
        except Exception as e:
            print(f"Lỗi kết nối PostgreSQL: {e}")
            return None
            
    else:
        # === KẾT NỐI VỚI SQLITE (Môi trường local/dev) ===
        conn = sqlite3.connect("database.db")
        conn.row_factory = sqlite3.Row
        return conn

# ----------------------------------------------------------------------
# HÀM KHỞI TẠO DATABASE TỰ ĐỘNG
# ----------------------------------------------------------------------

def init_app_db(conn):
    if conn and os.environ.get('DATABASE_URL'):
        try:
            cursor = conn.cursor()
            
            # TẠO BẢNG USERS (PostgreSQL)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                );
            """)
            
            # TẠO BẢNG POSTS (PostgreSQL)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL
                );
            """)
            
            conn.commit()
            cursor.close()
            print(">>> Khởi tạo/Kiểm tra bảng PostgreSQL thành công.")
        except Exception as e:
            print(f"LỖI KHỞI TẠO BẢNG: {e}")
            conn.rollback()

# ----------------------------------------------------------------------
# CÁC ROUTE VÀ LOGIC ỨNG DỤNG
# ----------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        if conn is None:
            return "Internal Server Error: Database Connection Failed.", 500

        try:
            if os.environ.get('DATABASE_URL'):
                # PostgreSQL: Dùng con trỏ và placeholder %s
                cur = conn.cursor()
                cur.execute("INSERT INTO users(username, password) VALUES(%s, %s)", (username, password))
                cur.close()
            else:
                # SQLite: Dùng conn.execute và placeholder ?
                conn.execute("INSERT INTO users(username, password) VALUES(?,?)", (username, password))
            
            conn.commit()
            
            # ⚠️ ĐÃ KHÓA: send_email(f"New user registered: {username}") 
            
            return redirect("/login")
            
        except Exception as e:
            print(f"LỖI ĐĂNG KÝ: {e}")
            conn.rollback()
            return "Internal Server Error: Database Query Failed.", 500
        finally:
            if conn:
                conn.close()

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        if conn is None:
            return "Internal Server Error: Database Connection Failed.", 500

        user = None
        try:
            if os.environ.get('DATABASE_URL'):
                # PostgreSQL: Dùng DictCursor để lấy kết quả bằng tên cột và placeholder %s
                cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                cur.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
                user = cur.fetchone()
                cur.close()
            else:
                # SQLite: Dùng conn.execute và placeholder ?
                user = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password)).fetchone()
            
        finally:
            if conn:
                conn.close()

        if user:
            session["user"] = user['username']
            return redirect("/dashboard")
        else:
            return "Sai tài khoản hoặc mật khẩu!"
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    if conn is None:
        return "Internal Server Error: Database Connection Failed.", 500
        
    user_count = 0
    try:
        if os.environ.get('DATABASE_URL'):
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM users")
            user_count = cur.fetchone()[0]
            cur.close()
        else:
            user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    finally:
        if conn:
            conn.close()
        
    file_count = len(os.listdir("uploads"))
    return render_template("dashboard.html", users=user_count, files=file_count)

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        file = request.files["file"]
        filename = secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_FOLDER, filename)) 
        return "Upload thành công!"
    return render_template("upload.html")

@app.route("/api/posts", methods=["GET"])
def api_get_posts():
    conn = get_db()
    if conn is None:
        return jsonify({"error": "Database Connection Failed"}), 500

    posts = []
    try:
        if os.environ.get('DATABASE_URL'):
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cur.execute("SELECT * FROM posts")
            posts = cur.fetchall()
            cur.close()
        else:
            posts = conn.execute("SELECT * FROM posts").fetchall()
    finally:
        if conn:
            conn.close()

    return jsonify([dict(row) for row in posts])

@app.route("/api/posts", methods=["POST"])
def api_add_post():
    data = request.json
    conn = get_db()
    if conn is None:
        return jsonify({"error": "Database Connection Failed"}), 500

    try:
        if os.environ.get('DATABASE_URL'):
            cur = conn.cursor()
            cur.execute("INSERT INTO posts(title, content) VALUES(%s, %s)", (data["title"], data["content"]))
            cur.close()
        else:
            conn.execute("INSERT INTO posts(title, content) VALUES(?,?)", (data["title"], data["content"]))
            
        conn.commit()
        return jsonify({"message": "Added"})
    except Exception as e:
        print(f"LỖI API POST: {e}")
        conn.rollback()
        return jsonify({"error": "Failed to add post"}), 500
    finally:
        if conn:
            conn.close()

# ----------------------------------------------------------------------
# HÀM GỬI EMAIL (ĐÃ KHÓA)
# ----------------------------------------------------------------------
def send_email(msg):
    # Chúng ta vô hiệu hóa hàm này để khắc phục lỗi Internal Server Error
    # sender = os.getenv("EMAIL")
    # password = os.getenv("EMAIL_PASS")
    # to = os.getenv("EMAIL")
    # context = ssl.create_default_context()
    # with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as s:
    #     s.login(sender, password)
    #     s.sendmail(sender, to, msg)
    pass # Lệnh này đảm bảo hàm không làm gì

# ----------------------------------------------------------------------
# CHẠY KHỞI TẠO DATABASE
# ----------------------------------------------------------------------
if __name__ != '__main__':
    db_connection = get_db()
    if db_connection:
        init_app_db(db_connection)
        db_connection.close()
