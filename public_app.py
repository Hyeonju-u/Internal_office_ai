# =====================================================================
# 공개 데모용 서버: 근로기준법 Q&A
# - 로그인 없음, 근로기준법 조문만 검색
# - 질문/답변/피드백을 public_logs 표에 저장 (평가셋 재료)
# =====================================================================
import re
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from ask import answer, THRESHOLD

app = Flask(__name__)
DB = "rules.db"
MAX_LEN = 300  # 질문 최대 길이 (너무 긴 입력 방지)


def init_db():
    """공개 데모 로그 표 (없을 때만 생성, 기존 기록은 유지)"""
    conn = sqlite3.connect(DB)
    cur = (
        conn.cursor()
    )  # sql 포인터 커서만드는것 sql 명령 전달,결과 데이터 가져오기 셀렉을 조회했을때 데이터 베이스가 돌려준 데이터를 임시로 담고있음 현재 위치기억(포인터역할)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS public_logs ( 
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT,
            question TEXT,
            answer TEXT,
            doc_titles TEXT,
            score REAL,
            feedback INTEGER        -- 1: 도움됨, -1: 도움 안 됨, NULL: 안 누름
        )
    """)
    conn.commit()  # 지금까지 한 작업(테이블 만들기) 데이터 베이스 파일에 완전히 저장하기
    conn.close()  # 데이터 베이스 연결된 통로 끊고 종료


# CREATE TABLE IF NOT EXISTS 이미 테이블이 존재하면 에러 내지않고 넘어가고 없을때만 public_logs 테이블 새로 만들어줘


def get_sources(doc_titles):
    """근거 조항 제목들 → [{title, text}] (화면에서 원문 펼치기용)"""
    # 제목에 쉼표가 들어간 조항도 있어서(예: 보고, 출석의 의무) 쉼표로 자르지 않고 패턴으로 뽑음
    titles = re.findall(
        r"근로기준법 제\d+조(?:의\d+)?\([^)]*\)", doc_titles or ""
    )  # re.findall 정규 표현식을 사용해서 문자열내 패턴과 일치하는 모든 부분을 찾아 리스트 형태로 반환하는 함수
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    sources = []
    for t in titles:
        cur.execute(
            "SELECT text FROM docs WHERE title = ?", (t,)
        )  # execute 파이썬에 작성한 sql 명령어를 데이터 베이스에 직접 전달하고 실행하는 명령어
        row = (
            cur.fetchone()
        )  # SQL로 조회한 결과 중에서 딱 한 줄(행, Row)만 가져오는 함수
        if row:
            sources.append({"title": t, "text": row[0]})
    conn.close()
    return sources


# 2. 메인 페이지(루트 경로) 라우트 정의
@app.route("/")
def home():
    # templates 폴더 안의 public.html을 찾아 렌더링함
    return render_template("public.html")


@app.route("/api/ask", methods=["POST"])
def api_ask():
    data = request.get_json(silent=True) or {}
    question = str(data.get("question", "")).strip()

    # 입력 검증 (서버 쪽이 진짜 방어)
    if not question:
        return jsonify({"error": "질문을 입력해주세요."}), 400
    if len(question) > MAX_LEN:
        return jsonify({"error": f"질문은 {MAX_LEN}자 이내로 입력해주세요."}), 400

    result, doc_titles, score = answer("공개", question, only_law=True)
    found = (score is not None and score >= THRESHOLD) and (
        "찾을 수 없습니다" not in result
    )
    sources = get_sources(doc_titles) if found else []  # 거절된 경우 근거 표시 안 함

    # 로그 저장
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO public_logs (created_at, question, answer, doc_titles, score) VALUES (?, ?, ?, ?, ?)",
        (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            question,
            result,
            doc_titles,
            score,
        ),
    )
    log_id = cur.lastrowid
    conn.commit()
    conn.close()

    return jsonify({"id": log_id, "answer": result, "found": found, "sources": sources})


@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    data = request.get_json(silent=True) or {}
    log_id = data.get("id")
    value = data.get("value")
    if not isinstance(log_id, int) or value not in (1, -1):
        return jsonify({"error": "잘못된 요청"}), 400

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("UPDATE public_logs SET feedback = ? WHERE id = ?", (value, log_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


init_db()
# 스크립트 직접 실행 시 서버 구동
if __name__ == "__main__":
    app.run(
        port=5001, debug=False
    )  # 공개용은 debug 끔 / 사내용(app.py, 5000)과 포트 분리
