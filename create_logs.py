import sqlite3

conn = sqlite3.connect("rules.db")
cur = conn.cursor()

# 로그는 쌓이는 기록이라 DROP 안 함 → 이미 있으면 그대로 둠
cur.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,      -- 언제
        username TEXT,        -- 누가
        dept TEXT,            -- 누가 (소속)
        question TEXT,        -- 무엇을
        answer TEXT,          -- 어떻게 됐나
        doc_title TEXT,       -- 어떤 문서로
        score REAL            -- 몇 점 (REAL = 소수점 숫자)
    )
""")

conn.commit()
conn.close()
print("로그 표 준비 완료")