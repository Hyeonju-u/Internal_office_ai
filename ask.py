import json
import math
import re
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


def generate(prompt):
    """Ollama에 프롬프트 보내고 답변 글자 받아오기"""
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
        return json.loads(res.read())["response"]


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

    # 3. 전부 점수 매기고 상위 3개
    scored = []
    for title, text, embedding in rows:
        c_vec = json.loads(embedding)
        score = cosine_similarity(q_vec, c_vec)
        scored.append((score, title, text))

    scored.sort(reverse=True)
    top = scored[:3]

    for score, title, _ in top:
        print(f"{score:.3f}  {title}")

    # 4. 검증: 1등이 기준 미만이면 거절
    THRESHOLD = 0.55
    if not top or top[0][0] < THRESHOLD:
        best_title = top[0][1] if top else None
        best_score = top[0][0] if top else None
        return "규정에서 찾을 수 없습니다.", best_title, best_score

    # 1등과 점수 차이가 작은 것만 함께 전달 (잡음 줄이기)
    MARGIN = 0.1
    best = top[0][0]
    passed = [(s, t, x) for s, t, x in top if s >= THRESHOLD and best - s <= MARGIN]
    context = "\n\n".join(x for _, _, x in passed)
    titles = ", ".join(t for _, t, _ in passed)

    # 5. 답변 생성
    prompt = f"""너는 회사 규정 안내 도우미야. 반드시 한국어로만 답해.
아래 [참고 문서]에 있는 내용만 근거로 답하고, 근거가 된 문서 이름과 조항 번호를 같이 말해.
(예: 근로기준법 제60조, 사내 규정 제12조)
참고 문서에 없는 내용이면 "규정에서 찾을 수 없습니다"라고 답해.

[참고 문서]
{context}

[질문]
{question}
"""
    result = generate(prompt)

    # 6. 출력 검증: 중국어(한자)가 섞였으면 한 번 다시 생성
    if re.search(r"[\u4e00-\u9fff]", result):
        print("⚠ 중국어 섞임 감지 → 재생성")
        result = generate(prompt + "\n\n주의: 이전 답변에 중국어가 섞였다. 한국어로만, 짧게 다시 답해.")

    return result, titles, best


# ---------- 테스트 ----------
if __name__ == "__main__":
    print(answer("영업팀", "입사 1년 지나면 연차 며칠이야?"))
    print(answer("영업팀", "야근하면 수당 더 받아?"))
    print(answer("영업팀", "점심시간은 몇 분 줘야 해?"))
    print(answer("영업팀", "법카 한도는?"))