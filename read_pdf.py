from pypdf import PdfReader

reader = PdfReader("근로기준법.pdf")
print("페이지 수:", len(reader.pages))

text = ""
for page in reader.pages:
    text += page.extract_text() + "\n"

# 뽑은 글자를 파일로 저장 (눈으로 확인용)
with open("근로기준법.txt", "w", encoding="utf-8") as f:
    f.write(text)

print(text[:1500])   # 앞부분만 화면에 출력