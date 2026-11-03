import json
import math
import re
import sqlite3
import urllib.request

W = 0.1            # 키워드 보너스 비중 (평가로 결정)
THRESHOLD = 0.60   # 거절 기준 (평가로 결정: 거절 정확도 100% 유지)
MARGIN = 0.1       # 1등과 점수 차이가 이 안쪽인 조항만 함께 전달


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


def bigrams(s):
    s = re.sub(r"[^가-힣a-zA-Z0-9]", "", s)
    return {s[i:i+2] for i in range(len(s) - 1)}


def generate(prompt):
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
    q_vec = get_embedding(question)
    q_grams = bigrams(question)

    # 1. DB에서 전체 조항 읽기 (IDF는 전체 기준으로 계산해야 해서)
    conn = sqlite3.connect("rules.db")
    cur = conn.cursor()
    cur.execute("SELECT title, dept, text, embedding FROM docs")
    all_rows = cur.fetchall()
    conn.close()

    # 2. 드문 정도(IDF) 계산
    doc_grams = [bigrams(title + text) for title, _, text, _ in all_rows]
    N = len(all_rows)
    df = {}
    for grams in doc_grams:
        for g in grams:
            df[g] = df.get(g, 0) + 1
    idf = {g: math.log(N / c) for g, c in df.items()}
    q_total = sum(idf[g] for g in q_grams if g in idf)

    # 3. 권한 있는 조항만 하이브리드 점수 계산
    scored = []
    for (title, dept, text, emb), grams in zip(all_rows, doc_grams):
        if dept != "전체" and dept != user_dept:      # ★ 권한 필터
            continue
        emb_score = cosine_similarity(q_vec, json.loads(emb))
        kw_score = (sum(idf[g] for g in q_grams & grams) / q_total) if q_total else 0
        scored.append((emb_score + W * kw_score, title, text))

    scored.sort(reverse=True)
    top = scored[:3]
    for score, title, _ in top:
        print(f"{score:.3f}  {title}")

    # 4. 검증: 1등이 기준 미만이면 거절
    if not top or top[0][0] < THRESHOLD:
        best_title = top[0][1] if top else None
        best_score = top[0][0] if top else None
        return "규정에서 찾을 수 없습니다.", best_title, best_score

    best = top[0][0]
    passed = [(s, t, x) for s, t, x in top if best - s <= MARGIN]
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

    # 6. 출력 검증: 중국어 섞이면 한 번 재생성
    if re.search(r"[\u4e00-\u9fff]", result):
        print("⚠ 중국어 섞임 감지 → 재생성")
        result = generate(prompt + "\n\n주의: 이전 답변에 중국어가 섞였다. 한국어로만, 짧게 다시 답해.")

    return result, titles, best


if __name__ == "__main__":
    print(answer("영업팀", "급여명세서 꼭 줘야 해?"))
    print(answer("영업팀", "야근하면 수당 더 받아?"))
    print(answer("영업팀", "임원 성과급 얼마까지 줘?"))
    print(answer("영업팀", "법카 한도는?"))