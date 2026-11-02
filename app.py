import sqlite3
from datetime import datetime
from flask import Flask, request, render_template_string, session, redirect
from werkzeug.security import check_password_hash
from ask import answer

app = Flask(__name__)
app.secret_key = "dev-secret-change-me"   # 세션 위조 방지용 비밀키 (실서비스에선 길고 랜덤하게)

# ---------- 화면 ----------
LOGIN_PAGE = """
<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>로그인</title></head>
<body style="font-family: sans-serif; max-width: 400px; margin: 60px auto;">
  <h2>사내 규정 AI 로그인</h2>
  <form method="post">
    <input name="username" placeholder="아이디" required style="width:100%; padding:8px;"><br><br>
    <input name="password" type="password" placeholder="비밀번호" required style="width:100%; padding:8px;"><br><br>
    <button type="submit">로그인</button>
  </form>
  {% if error %}<p style="color:red;">{{ error }}</p>{% endif %}
</body></html>
"""

ASK_PAGE = """
<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>사내 규정 AI</title></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 40px auto;">
  <p>{{ username }} ({{ dept }}) 님 · <a href="/logout">로그아웃</a></p>
  <h2>사내 규정 AI</h2>
  <form method="post">
    <input name="question" placeholder="질문을 입력하세요" required style="width:100%; padding:8px;"><br><br>
    <button type="submit">질문하기</button>
  </form>
  {% if result %}
    <hr>
    <p><b>{{ question }}</b></p>
    <p>{{ result }}</p>
  {% endif %}
</body></html>
"""

# ---------- 로그인 ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # DB에서 그 아이디의 해시와 부서 꺼내기
        conn = sqlite3.connect("rules.db")
        cur = conn.cursor()
        cur.execute("SELECT password_hash, dept FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        conn.close()

        # 아이디가 있고, 입력한 비번을 같은 방식으로 변환해서 일치하면 통과
        if row and check_password_hash(row[0], password):
            session["username"] = username
            session["dept"] = row[1]    # ★ 부서는 서버가 DB에서 확인한 값으로만 저장
            return redirect("/")

        return render_template_string(LOGIN_PAGE, error="아이디 또는 비밀번호가 틀렸습니다.")

    return render_template_string(LOGIN_PAGE)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------- 질문 화면 ----------
@app.route("/", methods=["GET", "POST"])
def home():
    if "username" not in session:
        return redirect("/login")

    username = session["username"]
    dept = session["dept"]   # ★ 화면이 아니라 세션(서버가 아는 값)에서 꺼냄

    if request.method == "POST":
        question = request.form["question"]

        # 빈 질문이면 AI 부르지 않고 바로 안내
        if question.strip() == "":
            return render_template_string(ASK_PAGE, username=username, dept=dept,question="", result="질문을 입력해주세요.")

        # 사내 AI 호출 (답변, 근거 문서, 점수)
        result, doc_title, score = answer(dept, question)

        # ---------- 로그 한 줄 저장 ----------
        conn = sqlite3.connect("rules.db")
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO logs (created_at, username, dept, question, answer, doc_title, score) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             username, dept, question, result, doc_title, score)
        )
        conn.commit()
        conn.close()

        return render_template_string(ASK_PAGE, username=username, dept=dept,
                                      question=question, result=result)

    return render_template_string(ASK_PAGE, username=username, dept=dept)

if __name__ == "__main__":
    app.run(debug=True)