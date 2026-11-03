import json
import math
import re
import sqlite3
from ask import get_embedding, cosine_similarity

# ---------- 두 글자씩 자르기 ----------
def bigrams(s):
    s = re.sub(r"[^가-힣a-zA-Z0-9]", "", s)   # 한글/영어/숫자만 남기고 붙이기
    return {s[i:i+2] for i in range(len(s) - 1)}

# 1. 시험지 + 조항 읽기
with open("eval_set.json", "r", encoding="utf-8") as f:
    tests = json.load(f)

conn = sqlite3.connect("rules.db")
cur = conn.cursor()
cur.execute("SELECT title, dept, text, embedding FROM docs")
docs = []
for title, dept, text, emb in cur.fetchall():
    docs.append({
        "title": title,
        "dept": dept,
        "vec": json.loads(emb),
        "grams": bigrams(title + text)     # 조항마다 두 글자 조각 미리 만들어둠
    })
conn.close()

# 2. 드문 정도(IDF) 계산: 적은 조항에 나오는 조각일수록 큰 값
N = len(docs)
df = {}                                    # 조각별로 "몇 개 조항에 나오나"
for d in docs:
    for g in d["grams"]:
        df[g] = df.get(g, 0) + 1
idf = {g: math.log(N / c) for g, c in df.items()}

def keyword_score(q_grams, doc_grams):
    """질문 조각 중 조항에 있는 것들의 IDF 합 ÷ 질문 조각 IDF 전체 합 (0~1)"""
    total = sum(idf[g] for g in q_grams if g in idf)
    if total == 0:
        return 0
    hit = sum(idf[g] for g in q_grams & doc_grams if g in idf)
    return hit / total

# 3. 문제마다 뜻 점수 + 키워드 점수 미리 계산
results = []
for i, t in enumerate(tests, start=1):
    q_vec = get_embedding(t["question"])
    q_grams = bigrams(t["question"])
    rows = []
    for d in docs:
        if d["dept"] != "전체" and d["dept"] != t["dept"]:
            continue
        rows.append((cosine_similarity(q_vec, d["vec"]),
                     keyword_score(q_grams, d["grams"]),
                     d["title"]))
    results.append({"test": t, "rows": rows})
    print(f"[{i}/{len(tests)}] {t['question']}")

# 4. 보너스 크기(W) × 기준값별 채점
def grade(W, threshold):
    top3_ok = answerable = reject_ok = rejectable = 0
    for r in results:
        t = r["test"]
        scored = sorted(((emb + W * kw, title) for emb, kw, title in r["rows"]), reverse=True)
        best_score = scored[0][0]
        top3 = [title for _, title in scored[:3]]
        passed = best_score >= threshold
        if t["expected"]:
            answerable += 1
            if passed and any(e in top3 for e in t["expected"]):
                top3_ok += 1
        else:
            rejectable += 1
            if not passed:
                reject_ok += 1
    return top3_ok / answerable, reject_ok / rejectable

print("\n  W  | 기준값 | Top-3 | 거절")
print("-----|--------|-------|------")
for W in [0.0, 0.1, 0.2, 0.3]:
    for th in [0.55, 0.60, 0.65, 0.70]:
        top3, rej = grade(W, th)
        mark = "  ★" if rej == 1.0 else ""     # 거절 100%인 조합 표시
        print(f" {W:.1f} |  {th:.2f}  | {top3:.0%}  | {rej:.0%}{mark}")