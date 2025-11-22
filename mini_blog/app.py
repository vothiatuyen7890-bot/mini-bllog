from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import sqlite3, os
from werkzeug.utils import secure_filename
import smtplib, ssl
import psycopg2
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = "secret123"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db():
    # Lấy DATABASE_URL từ Biến Môi trường của Render
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        # === KẾT NỐI VỚI POSTGRESQL (Môi trường Render) ===
        try:
            # Phân tích URL để lấy thông tin kết nối
            result = urlparse(db_url)
            username = result.username
            password = result.password
            database = result.path[1:]
            hostname = result.hostname
            port = result.port

            # Kết nối bằng psycopg2
            conn = psycopg2.connect(
                database=database,
                user=username,
                password=password,
                host=hostname,
                port=port
            )
            # Tùy chỉnh để có thể truy cập cột bằng tên (giống sqlite3.Row)
            conn.row_factory = psycopg2.extras.DictCursor # Sẽ phức tạp hơn

        except Exception as e:
            print(f"Lỗi kết nối PostgreSQL: {e}")
            # Nếu có lỗi, bạn nên xử lý lỗi ở đây, ví dụ: raise Exception(e)
            return None

    else:
        # === KẾT NỐI VỚI SQLITE (Môi trường local/dev) ===
        conn = sqlite3.connect("database.db")
        conn.row_factory = sqlite3.Row

    return conn
    # BỔ SUNG: Khởi tạo database tự động khi ứng dụng khởi động

def init_app_db(conn):
    # Hàm này sẽ được gọi ở cuối file để tạo bảng nếu chúng chưa tồn tại
    if conn:
        try:
            cursor = conn.cursor()
            # Thử tạo bảng USERS (PostgreSQL)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                );
            """)
            # Thử tạo bảng POSTS (PostgreSQL)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL
                );
            """)
            conn.commit()
            cursor.close()
            print(">>> Khởi tạo/Kiểm tra bảng database thành công.")
        except Exception as e:
            print(f"LỖI KHỞI TẠO BẢNG: {e}")
    else:
        print("LỖI: Không thể khởi tạo database vì kết nối thất bại.")


# ... (các hàm @app.route() của bạn) ...


# GỌI HÀM KHỞI TẠO CUỐI FILE (Sau khi app được định nghĩa)
if __name__ != '__main__': # Đảm bảo chỉ chạy khi Gunicorn khởi động (không chạy khi bạn chạy local)
    db_connection = get_db()
    if db_connection:
        init_app_db(db_connection)
        db_connection.close()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        conn.execute("INSERT INTO users(username, password) VALUES(?,?)", (username, password))
        conn.commit()

        send_email(f"New user registered: {username}")
        return redirect("/login")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password)).fetchone()

        if user:
            session["user"] = username
            return redirect("/dashboard")
        else:
            return "Sai tài khoản hoặc mật khẩu!"
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
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
    posts = conn.execute("SELECT * FROM posts").fetchall()
    return jsonify([dict(row) for row in posts])

@app.route("/api/posts", methods=["POST"])
def api_add_post():
    data = request.json
    conn = get_db()
    conn.execute("INSERT INTO posts(title, content) VALUES(?,?)", (data["title"], data["content"]))
    conn.commit()
    return jsonify({"message": "Added"})

def send_email(msg):
    sender = os.getenv("EMAIL")
    password = os.getenv("EMAIL_PASS")
    to = os.getenv("EMAIL")
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as s:
        s.login(sender, password)
        s.sendmail(sender, to, msg)


