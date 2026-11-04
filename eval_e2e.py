# =====================================================================
# 최종 답변 평가 (검색 + AI 답변까지 전부 거친 결과를 채점)
# 질문 바꿔 쓰기 끔 / 켬 두 가지를 비교
# =====================================================================
import csv
import json
from ask import answer, REFUSAL

with open("eval_set.json", "r", encoding="utf-8") as f:
    tests = json.load(f)


def judge(test, result, titles):
    """최종 결과가 맞았는지 판단"""
    refused = refused = "찾을 수 없" in result     # 표현이 조금 달라도 거절로 인정
    if not test["expected"]:                       # 거절해야 하는 문제
        return refused
    if refused:                                   # 답해야 하는데 거절함
        return False
    return any(e in (titles or "") for e in test["expected"])   # 정답 조항을 근거로 썼나


rows = []
summary = {}

for mode, use_rewrite in [("바꿔쓰기 켬", True)]:
    ans_ok = ans_total = rej_ok = rej_total = 0
    for i, t in enumerate(tests, start=1):
        print(f"\n[{mode}] {i}/{len(tests)} {t['question']}")
        result, titles, score = answer(t["dept"], t["question"], use_rewrite=use_rewrite)
        ok = judge(t, result, titles)

        if t["expected"]:
            ans_total += 1
            ans_ok += ok
        else:
            rej_total += 1
            rej_ok += ok

        rows.append({
            "mode": mode,
            "question": t["question"],
            "type": "답변" if t["expected"] else "거절",
            "ok": "O" if ok else "X",
            "score": f"{score:.3f}" if score is not None else "",
            "titles": titles or "",
            "answer": result.replace("\n", " ")[:120]
        })

    summary[mode] = (ans_ok, ans_total, rej_ok, rej_total)

# 결과 표
print("\n\n모드          | 답해야 할 것 정답 | 거절 정확도 | 전체")
print("--------------|-------------------|-------------|------")
for mode, (a_ok, a_t, r_ok, r_t) in summary.items():
    total = (a_ok + r_ok) / (a_t + r_t)
    print(f"{mode} | {a_ok}/{a_t} ({a_ok/a_t:.0%})       | {r_ok}/{r_t} ({r_ok/r_t:.0%})  | {total:.0%}")

# 문제별 상세 결과 저장 (엑셀로 열어서 볼 수 있음)
with open("eval_e2e_result.csv", "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
print("\n상세 결과: eval_e2e_result.csv")
