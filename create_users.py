import sqlite3
from werkzeug.security import generate_password_hash   # 비밀번호 해시 변환 (Flask에 딸려옴)

conn = sqlite3.connect("rules.db")   # 같은 DB 파일에 표만 하나 더 추가
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS users")
cur.execute("""
    CREATE TABLE users (
        username TEXT PRIMARY KEY,   -- 아이디 (중복 불가)
        password_hash TEXT,          -- 비밀번호 원본 X, 변환된 값만 저장
        dept TEXT                    -- 부서
    )
""")

# 테스트용 직원 3명
users = [
    ("kim", "1234", "영업팀"),
    ("lee", "1234", "인사팀"),
    ("park", "1234", "생산팀"),
]

for username, password, dept in users:
    cur.execute(
        "INSERT INTO users (username, password_hash, dept) VALUES (?, ?, ?)",
        (username, generate_password_hash(password), dept)
    )
    print(f"등록: {username} ({dept})")

conn.commit()
conn.close()
print("직원 등록 완료")