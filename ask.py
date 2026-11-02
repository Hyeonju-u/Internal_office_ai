import json
import math
import sqlite3
import urllib.request

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

def cosine_similarity(a, b):
    dot = 0
    for i in range(len(a)):
        dot += a[i] * b[i]
    len_a = math.sqrt(sum(x * x for x in a))
    len_b = math.sqrt(sum(x * x for x in b))
    return dot / (len_a * len_b)

def answer(user_dept, question):
    # 1. 질문만 좌표로 변환
    q_vec = get_embedding(question)

    # 2. DB에서 내 부서가 볼 수 있는 조항만 꺼내기
    conn = sqlite3.connect("rules.db")
    cur = conn.cursor()
    cur.execute(
        "SELECT title, text, embedding FROM docs WHERE dept = '전체' OR dept = ?",
        (user_dept,)
    )
    rows = cur.fetchall()
    conn.close()

    # 3. 점수 비교
    best_score = -1
    best_text = None
    best_title = None
    for title, text, embedding in rows:
        c_vec = json.loads(embedding)
        score = cosine_similarity(q_vec, c_vec)
        print(f"{score:.3f}  {title}")   # 확인용 (서버 로그에 찍힘)
        if score > best_score:
            best_score = score
            best_text = text
            best_title = title

    # 4. 검증: 점수 낮으면 AI 안 거치고 바로 돌려주기
    THRESHOLD = 0.55
    if best_text is None or best_score < THRESHOLD:
        return "규정에서 찾을 수 없습니다.", best_title, best_score

    # 5. 답변 생성
    prompt = f"""너는 회사 규정 안내 도우미야. 반드시 한국어로만 답해.
아래 [사내 규정]에 있는 내용만 근거로 답하고, 근거가 된 조항 번호를 같이 말해.
규정에 없는 내용이면 "규정에서 찾을 수 없습니다"라고 답해.

[사내 규정]
{best_text}

[질문]
{question}
"""
    data = {
        "model": "qwen2.5:7b",
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0}
    }
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as res:
        result = json.loads(res.read())["response"]

    return result, best_title, best_score


# ---------- 테스트 ----------
if __name__ == "__main__":
    print(answer("영업팀", "호텔비 얼마야?"))
    print(answer("영업팀", "임원 성과급 얼마까지 줘?"))
    print(answer("인사팀", "임원 성과급 얼마까지 줘?"))