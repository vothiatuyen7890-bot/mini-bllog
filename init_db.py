import psycopg2
import os
from urllib.parse import urlparse

# Lấy chuỗi kết nối PostgreSQL từ Biến Môi trường của Render
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("LỖI: Biến môi trường DATABASE_URL không được tìm thấy. Không thể khởi tạo database.")
    exit(1)

# Phân tích URL và thiết lập kết nối
try:
    result = urlparse(DATABASE_URL)
    username = result.username
    password = result.password
    database = result.path[1:]
    hostname = result.hostname
    port = result.port

    conn = psycopg2.connect(
        database=database,
        user=username,
        password=password,
        host=hostname,
        port=port
    )
    cursor = conn.cursor()

    # XÓA BẢNG CŨ (TÙY CHỌN - nếu bạn muốn khởi tạo lại)
    cursor.execute("DROP TABLE IF EXISTS users;")
    cursor.execute("DROP TABLE IF EXISTS posts;")

    # TẠO BẢNG USERS
    cursor.execute("""
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );
    """)

    # TẠO BẢNG POSTS
    cursor.execute("""
        CREATE TABLE posts (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL
        );
    """)

    # THÊM DỮ LIỆU MẪU (TÙY CHỌN)
    # cursor.execute("INSERT INTO users (username, password) VALUES ('admin', 'adminpass');")

    conn.commit()
    cursor.close()
    conn.close()
    print("Khởi tạo database PostgreSQL thành công: Đã tạo bảng users và posts.")

except Exception as e:
    print(f"LỖI KHỞI TẠO DATABASE: {e}")
    exit(1)
