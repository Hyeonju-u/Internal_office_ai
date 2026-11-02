# =====================================================================
# 사내 규정 Q&A (RAG) - 권한 필터 + 점수 검증 버전
# 흐름: 규정 자르기 → 권한 확인 → 뜻 검색 → 점수 검증 → AI 답변
# =====================================================================

import json # 파이썬 데이터랑 json 글자 변환 (Ollama와 대화할 때 씀)
import math # 제곱근(sart) 계산용
import urllib.request #내 노트북안이 Ollama 서버에 요청 보내기용

# ---------- 부품 1: 문장 → 좌표(숫자 1024개)로 바꾸기----------
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

# ---------------------------------------------------------------------
# 부품 2: 두 좌표가 얼마나 같은 방향인지 점수 내기 (코사인 유사도)
# 1에 가까움 = 뜻이 비슷 / 0 근처 = 상관없음 / -1 = 정반대
# ---------------------------------------------------------------------
#같은 위치끼리 곱해서 전부 더하기 같은 방향이면 플러스가 쌓이고 반대 방향이면 마이너스가 쌓임
def cosine_similarity(a, b):
    dot = 0
    for i in range(len(a)):
        dot += a[i] * b[i]
    # ② 각 좌표의 길이 (피타고라스: √(x² + y² + ...))    
    len_a = math.sqrt(sum(x * x for x in a))
    len_b = math.sqrt(sum(x * x for x in b))
    # ③ 길이로 나누기
    #    안 나누면 [3,4]와 [30,40]처럼 방향은 같은데 길이만 다른 경우
    #    점수가 10배 차이남 → 길이 영향을 없애고 "방향"만 비교하려고 나눔
    return dot / (len_a * len_b)

# ---------------------------------------------------------------------
# 부품 3: 규정 파일을 조항 단위로 자르고, 조항마다 부서 정보 뽑기
# 파일 형식: [제12조 연차휴가 | 전체]
#            [제20조 임원보수 | 인사팀]
# ---------------------------------------------------------------------
with open("규정.txt", "r", encoding="utf-8") as f:
    rules = f.read() #파일 전체를 글자 하나로 읽음

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

# ---------- 사용자 정보 (지금은 직접 입력 → 나중에 Flask 로그인 정보로 대체) ----------
user_dept = "인사팀"
question = "임원 성과급 얼마까지 줘?"

# ---------- 권한 필터 + 검색 ----------
q_vec = get_embedding(question)  # 질문도 좌표로 변환
best_score = -1  # 지금까지 최고 점수 (어떤 점수든 이보다 크도록 -1로 시작)
best_doc = None   # 지금까지 1등 조항 (아직 없음)

for doc in docs:
    # 권한 확인: 전체 공개도 아니고 내 부서 문서도 아니면 건너뛰기
    # ★ 권한 확인을 검색 "전에" 하는 이유:
    #   AI한테 모든 문서를 주고 "인사팀 거는 말하지 마"라고 시키면
    #   AI가 실수하거나 질문 한 줄에 속을 수 있음.
    #   처음부터 못 보게 막으면, AI는 볼 수 없는 걸 말할 수도 없음.
    #
    # ★ and인 이유: 두 조건이 "둘 다" 참일 때만 차단
    #   - 전체 공개 문서가 아니고
    #   - 내 부서 문서도 아닐 때
    #   → 둘 중 하나라도 해당하면(전체 공개거나 내 부서면) 통과
    if doc["dept"] != "전체" and doc["dept"] != user_dept:
        print(f"(차단됨)  {doc['title']}  ← {doc['dept']} 전용")
        continue # 좌표 계산도 안 하고 다음 조항으로

    c_vec = get_embedding(doc["text"])# 조항을 좌표로 변환
    score = cosine_similarity(q_vec, c_vec)# 질문과 비교한 점수
    print(f"{score:.3f}  {doc['title']}") # .3f = 소수점 셋째 자리까지
# 1등 갱신: 이번 점수가 지금까지 최고보다 높으면 기록 교체
    if score > best_score:
        best_score = score
        best_doc = doc # 좌표(c_vec)가 아니라 조항 자체를 저장 (AI한테 줄 건 글자니까)

# ---------------------------------------------------------------------
# 검증: 점수가 기준 미만이면 AI한테 안 보내고 바로 종료
# ---------------------------------------------------------------------
# THRESHOLD = 합격선 (질문마다 바뀌는 값이 아니라 미리 정한 고정 숫자)
# 테스트해보니 관련 있으면 0.63 이상, 상관없으면 0.47 정도 → 그 사이 0.5
THRESHOLD = 0.5
# 이걸 하는 이유:
#   1) 작은 모델은 상관없는 조항을 받으면 억지로 엮어서 지어낼 수 있음
#   2) 답할 게 없는 질문에 AI를 돌리는 시간 낭비 방지
#   3) best_doc이 None = 볼 수 있는 문서가 하나도 없었던 경우도 같이 처리
if best_doc is None or best_score < THRESHOLD:
    print("\n답변:")
    print("규정에서 찾을 수 없습니다.")
    exit() # 여기서 프로그램 끝 → 아래 AI 답변 부분 실행 안 됨

print("\n가장 관련 있는 조항:")
print(best_doc["text"])

# ---------------------------------------------------------------------
# 답변 생성: 찾은 조항 "하나만" AI한테 넘기기 (오픈북 시험)
# 규정 전체를 안 넘기는 이유: 문서가 길면 AI가 한 번에 못 읽고, 중간 내용을 놓침
# ---------------------------------------------------------------------
prompt = f"""너는 회사 규정 안내 도우미야. 반드시 한국어로만 답해.
아래 [사내 규정]에 있는 내용만 근거로 답하고, 근거가 된 조항 번호를 같이 말해.
규정에 없는 내용이면 "규정에서 찾을 수 없습니다"라고 답해.

[사내 규정]
{best_doc["text"]}

[질문]
{question}
"""

data = {
    "model": "qwen2.5:7b", # 답변 만드는 모델
    "prompt": prompt,
    "stream": False,# 답을 한 번에 다 받기 (글자씩 나눠 받지 않음)
    "options": {"temperature": 0}# 랜덤성 0 → 같은 질문엔 항상 같은 답
}

req = urllib.request.Request(
    "http://localhost:11434/api/generate",
    data=json.dumps(data).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

with urllib.request.urlopen(req) as res:
    print("\n답변:")
    print(json.loads(res.read())["response"])