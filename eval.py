import json
import sqlite3
from ask import get_embedding, cosine_similarity   # ask.py의 함수 빌려오기

# 1. 시험지 읽기
with open("eval_set.json", "r", encoding="utf-8") as f:
    tests = json.load(f)
print(f"문제 수: {len(tests)}")

# 2. DB에서 전체 조항 한 번만 읽어두기 (문제마다 다시 읽으면 느림)
conn = sqlite3.connect("rules.db")
cur = conn.cursor()
cur.execute("SELECT title, dept, embedding FROM docs")
all_docs = [(t, d, json.loads(e)) for t, d, e in cur.fetchall()]
conn.close()

# 3. 문제마다 점수 계산 (기준값과 상관없이 한 번만)
results = []
for i, t in enumerate(tests, start=1):
    q_vec = get_embedding(t["question"])
    scored = []
    for title, dept, vec in all_docs:
        if dept != "전체" and dept != t["dept"]:   # 권한 필터 (ask.py와 동일)
            continue
        scored.append((cosine_similarity(q_vec, vec), title))
    scored.sort(reverse=True)
    results.append({"test": t, "top": scored[:3]})
    print(f"[{i}/{len(tests)}] {t['question']}")

# 4. 기준값별 채점
def grade(threshold):
    top1_ok = top3_ok = answerable = 0
    reject_ok = rejectable = 0
    fails = []

    for r in results:
        t, top = r["test"], r["top"]
        best_score, best_title = top[0]
        top3_titles = [title for _, title in top]
        passed = best_score >= threshold

        if t["expected"]:                       # 답이 있어야 하는 문제
            answerable += 1
            if passed and best_title in t["expected"]:
                top1_ok += 1
            if passed and any(e in top3_titles for e in t["expected"]):
                top3_ok += 1
            else:
                fails.append(f"놓침   | {t['question']} → 1등 {best_title} ({best_score:.3f})")
        else:                                   # 거절해야 하는 문제
            rejectable += 1
            if not passed:
                reject_ok += 1
            else:
                fails.append(f"오답변 | {t['question']} → 1등 {best_title} ({best_score:.3f})")

    return {
        "top1": top1_ok / answerable,
        "top3": top3_ok / answerable,
        "reject": reject_ok / rejectable,
        "fails": fails
    }

# 5. 결과 표
print("\n기준값 | Top-1 | Top-3 | 거절 정확도")
print("-------|-------|-------|-----------")
for th in [0.50, 0.55, 0.60]:
    g = grade(th)
    print(f" {th:.2f}  | {g['top1']:.0%}  | {g['top3']:.0%}  | {g['reject']:.0%}")

# 6. 현재 기준(0.55)에서 틀린 문제 목록
print("\n[0.55 기준 틀린 문제]")
for line in grade(0.55)["fails"]:
    print(line)