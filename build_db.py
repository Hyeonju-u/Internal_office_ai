import json
import re
import sqlite3
import urllib.request

# ---------- 좌표 받아오기 ----------
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


# ---------- 문서 1: 사내 규정 (부서 권한 테스트용) ----------
def load_company_rules():
    with open("규정.txt", "r", encoding="utf-8") as f:
        rules = f.read()

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
    return docs


# ---------- 문서 2: 근로기준법 (전체 공개) ----------
def load_labor_law():
    with open("근로기준법.txt", "r", encoding="utf-8") as f:
        text = f.read()

    pattern = r"제(\d+)조(의\d+)?\("

    # 조항 시작 위치 + 부칙 감지
    starts = []
    prev_num = 0
    body_end = len(text)
    for m in re.finditer(pattern, text):
        num = int(m.group(1))
        if num < prev_num:
            bu = text.rfind("부칙", 0, m.start())
            body_end = bu if bu != -1 else m.start()
            break
        starts.append(m.start())
        prev_num = num

    # 조각 잘라내기
    chunks = []
    for i in range(len(starts)):
        start = starts[i]
        end = starts[i + 1] if i + 1 < len(starts) else body_end
        chunks.append(text[start:end].strip())

    # 중복 제거 + 개정 표시 지우기
    seen = set()
    docs = []
    for c in chunks:
        title = c.split(")")[0] + ")"
        if title in seen:
            continue
        seen.add(title)

        clean = re.sub(r"<[^>]*>", "", c)   # <개정 ...>, <신설 ...> 등 제거
        docs.append({
            "title": "근로기준법 " + title,   # 사내 규정 제12조와 구분되게 앞에 법 이름 붙임
            "dept": "전체",
            "text": "[근로기준법] " + clean
        })
    return docs


# ---------- DB 저장 ----------
docs = load_company_rules() + load_labor_law()
print(f"총 {len(docs)}개 조항 저장 시작")

conn = sqlite3.connect("rules.db")
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS docs")   # docs 표만 새로 만듦 (users, logs는 그대로)
cur.execute("""
    CREATE TABLE docs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        dept TEXT,
        text TEXT,
        embedding TEXT
    )
""")

for i, doc in enumerate(docs, start=1):
    vec = get_embedding(doc["text"])
    cur.execute(
        "INSERT INTO docs (title, dept, text, embedding) VALUES (?, ?, ?, ?)",
        (doc["title"], doc["dept"], doc["text"], json.dumps(vec))
    )
    print(f"[{i}/{len(docs)}] {doc['title']}")

conn.commit()
conn.close()
print("DB 저장 완료")