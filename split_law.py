import re

with open("근로기준법.txt", "r", encoding="utf-8") as f:
    text = f.read()

pattern = r"제(\d+)조(의\d+)?\("

# 1. 조항 시작 위치 찾기 + 부칙 감지
starts = []
prev_num = 0
body_end = len(text)

for m in re.finditer(pattern, text):
    num = int(m.group(1))
    if num < prev_num:
        # 부칙 제1조 위치에서 거꾸로 가장 가까운 "부칙" 찾기 → 거기가 본문 끝
        bu = text.rfind("부칙", 0, m.start())
        body_end = bu if bu != -1 else m.start()
        print(f"부칙 시작 감지: 제{prev_num}조 다음에 제{num}조")
        break
    starts.append(m.start())
    prev_num = num

# 2. 조각 잘라내기
chunks = []
for i in range(len(starts)):
    start = starts[i]
    end = starts[i + 1] if i + 1 < len(starts) else body_end
    chunks.append(text[start:end].strip())

# 3. 같은 조항 제목이 또 나오면 먼저 나온 것만 남기기
seen = set()          # 이미 나온 제목 기록장
unique_chunks = []
for c in chunks:
    title = c.split(")")[0] + ")"     # "제116조(과태료)"
    if title in seen:
        print(f"중복 제거: {title}")
        continue
    seen.add(title)
    unique_chunks.append(c)

print("최종 조항 수:", len(unique_chunks))

# 4. 확인
print("\n--- 뒤쪽 ---")
for c in unique_chunks[-5:]:
    print(c.split("\n")[0][:40])

print("\n--- 마지막 조항 끝부분 ---")
print(unique_chunks[-1][-200:])