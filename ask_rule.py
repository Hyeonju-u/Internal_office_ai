import json
import urllib.request

# 1. 규정 파일 읽기
with open("규정.txt", "r", encoding="utf-8") as f:
    rules = f.read()

question = "출장가서 밥값나와?"

# 2. 규정 + 질문을 합쳐서 프롬프트 만들기
prompt = f"""너는 회사 규정 안내 도우미야. 반드시 한국어로 답해.
아래 [사내 규정]에 있는 내용만 근거로 답하고, 근거가 된 조항 번호를 같이 말해.
규정에 없는 내용이면 "규정에서 찾을 수 없습니다"라고 답해.

[사내 규정]
{rules}

[질문]
{question}
"""

data = {"model": "qwen2.5:7b", "prompt": prompt, "stream": False}

req = urllib.request.Request(
    "http://localhost:11434/api/generate",
    data=json.dumps(data).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

with urllib.request.urlopen(req) as res:
    print(json.loads(res.read())["response"])