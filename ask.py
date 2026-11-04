import json
import math
import re
import sqlite3
import urllib.request

W = 0.1            # 키워드 보너스 비중 (평가로 결정)
THRESHOLD = 0.60   # 거절 기준 (평가로 결정)
MARGIN = 0.1       # 1등과 점수 차이가 이 안쪽인 조항만 함께 전달
REFUSAL = "규정에서 찾을 수 없습니다"


# ---------------------------------------------------------------------
# 부품 함수들
# ---------------------------------------------------------------------
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


def rewrite_query(question):
    """일상 표현 질문을 근로기준법 검색용 용어로 바꿔 쓰기
    예시는 평가셋에 없는 표현(알바, 사장님, 수습)만 사용 → 평가셋 커닝 방지"""
    prompt = f"""아래 질문을 근로기준법 조문을 검색하기 좋은 법률 용어 키워드로 바꿔줘.
일상 표현은 법률 용어로 바꾸고, 관련 개념도 2~3개 덧붙여.
키워드만 한 줄로 출력하고 다른 말은 쓰지 마. 반드시 한국어로.

예시)
질문: 알바도 쉬는 날 챙겨줘야 해?
키워드: 단시간근로자 유급휴일 주휴일 근로조건

질문: 사장님이 수습 끝나고 월급 깎아도 돼?
키워드: 사용자 수습기간 임금 감액 근로조건 변경

질문: {question}
키워드:"""
    result = generate(prompt).strip().split("\n")[0]
    result = re.sub(r"^\s*키워드\s*[:：]\s*", "", result)
    return result


def can_answer(question, context):
    """① 판단 단계: 넘겨받은 문서로 답할 수 있는 질문인지 예/아니오만 판단 (깐깐하게)
    평가셋 주제를 직접 쓰지 않고 일반 원칙으로만 지시 → 커닝 방지"""
    prompt = f"""너는 질문 분류기야. 아래 [참고 문서]가 [질문]에 직접 답할 수 있는 근거 조항을 담고 있는지만 판단해.

판단 기준:
- 질문 표현이 일상 말투여도, 참고 문서가 그 주제를 직접 규정하고 있으면 "예"
- 참고 문서가 비슷한 분야일 뿐 질문의 핵심 주제를 규정하지 않으면 "아니오"
- 질문이 참고 문서가 아닌 다른 법률이나 제도에 관한 것이면 "아니오"

"예" 또는 "아니오" 한 단어만 출력해.

[참고 문서]
{context}

[질문]
{question}

판단:"""
    result = generate(prompt).strip()
    return result.startswith("예")


def cited_articles_ok(result, titles):
    """③ 인용 검사(코드): 답변에 나온 '제N조'가 실제로 넘겨준 문서 안에 있는지 확인"""
    allowed = set(re.findall(r"제\d+조(?:의\d+)?", titles))
    cited = set(re.findall(r"제\s*\d+\s*조(?:\s*의\s*\d+)?", result))
    cited = {re.sub(r"\s", "", c) for c in cited}        # "제20조의 2" → "제20조의2"
    bad = cited - allowed
    if bad:
        print(f"⚠ 넘겨주지 않은 조항 인용: {bad}")
    return not bad


# ---------------------------------------------------------------------
# 메인: 부서 + 질문 → (답변, 근거 조항 제목들, 1등 점수)
# ---------------------------------------------------------------------
def answer(user_dept, question, only_law=False, use_rewrite=True):
    # 0. 질문 바꿔 쓰기
    if use_rewrite:
        rewritten = rewrite_query(question)
        print(f"[바꿔 쓰기] {rewritten}")
        search_text = question + " " + rewritten
    else:
        search_text = question
    q_vec = get_embedding(search_text)
    q_grams = bigrams(search_text)

    # 1. DB에서 전체 조항 읽기
    conn = sqlite3.connect("rules.db")
    cur = conn.cursor()
    cur.execute("SELECT title, dept, text, embedding FROM docs")
    all_rows = cur.fetchall()
    conn.close()

    # 2. IDF 계산
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
        if only_law and not title.startswith("근로기준법"):
            continue
        emb_score = cosine_similarity(q_vec, json.loads(emb))
        kw_score = (sum(idf[g] for g in q_grams & grams) / q_total) if q_total else 0
        scored.append((emb_score + W * kw_score, title, text))

    scored.sort(reverse=True)
    top = scored[:3]
    for score, title, _ in top:
        print(f"{score:.3f}  {title}")

    # 4. 1차 검증: 검색 점수 기준
    if not top or top[0][0] < THRESHOLD:
        best_title = top[0][1] if top else None
        best_score = top[0][0] if top else None
        return REFUSAL + ".", best_title, best_score

    best = top[0][0]
    passed = [(s, t, x) for s, t, x in top if best - s <= MARGIN]
    context = "\n\n".join(x for _, _, x in passed)
    titles = ", ".join(t for _, t, _ in passed)

    # 5. 2차 검증: 답할 수 있는 질문인지 판단 단계 (깐깐하게)
    # if not can_answer(question, context):
    #     print("⚠ 판단 단계에서 거절")
    #     return REFUSAL + ".", titles, best

    # 6. 답변 생성 (친절하게)
    prompt = f"""너는 근로기준법과 사내 규정 안내 도우미야. 반드시 한국어로만 답해.

규칙:
1. 아래 [참고 문서]만 근거로 답하고, 문서에 없는 내용은 지어내지 마.
2. 질문이 일상 말투라서 문서와 표현이 달라도, 문서 내용으로 답할 수 있으면 답해.
3. "~해도 돼?", "괜찮아?"처럼 판단을 묻는 질문은 문서에 적힌 기준을 설명하고,
   마지막에 "구체적인 상황 판단은 고용노동부(1350)나 노무사 상담을 권합니다."를 덧붙여.
4. 참고 문서가 질문 주제와 전혀 관련이 없을 때만 "{REFUSAL}"라고만 답해.
5. 근거가 된 문서 이름과 조항 번호를 밝혀. (예: 근로기준법 제60조)

[참고 문서]
{context}

[질문]
{question}
"""
    result = generate(prompt)

    # 7. 출력 검증: 중국어 섞이면 한 번 재생성
    if re.search(r"[\u4e00-\u9fff]", result):
        print("⚠ 중국어 섞임 감지 → 재생성")
        result = generate(prompt + "\n\n주의: 이전 답변에 중국어가 섞였다. 한국어로만, 짧게 다시 답해.")

    # 8. 3차 검증: 넘겨주지 않은 조항을 인용했으면 거절 (코드로 검사)
    if not cited_articles_ok(result, titles):
        return REFUSAL + ".", titles, best

    return result, titles, best


# ---------- 테스트 ----------
if __name__ == "__main__":
    print(answer("영업팀", "육아휴직 재직 몇 년 지나야 쓸 수 있어?", only_law=True))
    print(answer("영업팀", "당일 퇴사해도 돼?", only_law=True))
    print(answer("영업팀", "해고 통보를 문자로 받았는데 괜찮은 거야?", only_law=True))
