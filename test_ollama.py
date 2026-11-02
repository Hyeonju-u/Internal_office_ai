import json
import urllib.request

data = {
    "model": "qwen2.5:7b",
    "prompt": "연차 휴가 규정을 한 줄로 설명해줘",
    "stream": False
}

req = urllib.request.Request(
    "http://localhost:11434/api/generate",
    data=json.dumps(data).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

with urllib.request.urlopen(req) as res:
    result = json.loads(res.read())
    print(result["response"])