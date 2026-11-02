import sqlite3
import json # 파이썬 데이터랑 json 글자 변환 (Ollama와 대화할 때 씀)
import math # 제곱근(sart) 계산용
import urllib.request #내 노트북안이 Ollama 서버에 요청 보내기용

with open("규정.txt","r",encoding="utf-8") as f:
        rules = f.read() #규정 읽기
docs = [] #조항들을 담을 목록
for chunk in rules.split("["): # "["를 기준으로 조항마다 자르기
     # 파일이 "["로 시작해서, 첫 "[" 앞의 빈칸이 ''로 생김 → 건너뛰기
    if chunk == '':
        continue
    # "]" 앞부분 = 제목 줄 → "제12조 연차휴가 | 전체"
    header = chunk.split("]")[0]            # "제12조 연차휴가 | 전체"
    # "|"로 한 번 더 자르기 (텍스트 나누기 두 번째)
    # → title = "제12조 연차휴가 ", dept = " 전체"
    title, dept = header.split("|")          # 제목 / 부서로 나누기
    # 한 조항을 제목/부서/본문 세 칸짜리 한 줄로 저장
    docs.append({
        "title": title.strip(),              # strip(): 앞뒤 공백 제거
        "dept": dept.strip(),
        "text": "[" + chunk.strip()  # split이 버린 "["를 다시 붙임
    })
def get_embedding(text):
    data = {"model": "bge-m3", "input": text}
    #bge-m3 문장의 뜻을 좌표로 바꿔주는 임베딩 모델
    #localhost= 내 컴퓨터 자신+데이터가 노트북 밖으로 안나감(보안 핵심)
    req = urllib.request.Request(
        "http://localhost:11434/api/embed",
        data=json.dumps(data).encode("utf-8"),# 파이썬 dict → JSON 글자 → 바이트
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as res:
        result = json.loads(res.read()) # 받은 JSON → 파이썬 dict
    # 결과가 [[숫자들]] 처럼 목록 안에 목록으로 와서 첫 번째 것만 꺼냄    
    return result["embeddings"][0]
# 3. DB 파일을 열고, 표(테이블)를 만든다
conn = sqlite3.connect("rules.db")   # rules.db 파일 열기 (없으면 새로 만듦)
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS docs")   # 다시 실행할 때 예전 표 지우고 새로 시작
cur.execute("""
    CREATE TABLE docs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,   -- 줄 번호 (자동으로 1, 2, 3...)
        title TEXT,
        dept TEXT,
        text TEXT,
        embedding TEXT                          -- 좌표를 글자로 바꿔서 저장
    )
""")

# 4. 조항마다 좌표로 바꾸고 표에 한 줄씩 저장
def get_embedding(text):
    data = {"model": "bge-m3", "input": text}
    req = urllib.request.Request(
        "http://localhost:11434/api/embed",
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as res:
        result = json.loads(res.read())
    return result["embeddings"][0]

# 1. 규정 읽기
with open("규정.txt", "r", encoding="utf-8") as f:
    rules = f.read()

# 2. 조항 단위로 자르고 제목/부서/본문 뽑기
docs = []
for chunk in rules.split("["):
    if chunk == '':
        continue
    header = chunk.split("]")[0]
    title, dept = header.split("|")
    docs.append({
        "title": title.strip(),
        "dept": dept.strip(),
        "text": "[" + chunk.strip()
    })

# 3. DB 파일 열고 표 만들기
conn = sqlite3.connect("rules.db")
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS docs")
cur.execute("""
    CREATE TABLE docs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        dept TEXT,
        text TEXT,
        embedding TEXT
    )
""")

# 4. 조항마다 좌표로 바꾸고 한 줄씩 저장
for doc in docs:
    vec = get_embedding(doc["text"])
    cur.execute(
        "INSERT INTO docs (title, dept, text, embedding) VALUES (?, ?, ?, ?)",
        (doc["title"], doc["dept"], doc["text"], json.dumps(vec))
    )
    print(f"저장: {doc['title']}")

# 5. 저장 확정하고 닫기
conn.commit()
conn.close()
print("DB 저장 완료")