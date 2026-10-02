import os, sqlite3, secrets, time
from flask import Flask, request, redirect, session, render_template_string, abort

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
STAFF_PASSWORD = os.environ.get("STAFF_PASSWORD", "changeme")   # set this before going live
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
STATUSES = ["New", "Seen", "Under Consideration", "In Progress", "Resolved", "Closed", "Rejected"]
_ready = False

def run(sql, args=(), fetch=False):
    """Runs one query. Postgres on Vercel (DATABASE_URL set), SQLite for local testing."""
    global _ready
    if DATABASE_URL:
        import psycopg2, psycopg2.extras
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor); sql = sql.replace("?", "%s")
    else:
        import sqlite3
        conn = sqlite3.connect("helpdesk.db"); conn.row_factory = sqlite3.Row; cur = conn.cursor()
    try:
        if not _ready:
            cur.execute("""CREATE TABLE IF NOT EXISTS tickets(
                id TEXT PRIMARY KEY, name TEXT, pc TEXT, description TEXT,
                status TEXT DEFAULT 'New', notes TEXT DEFAULT '', created DOUBLE PRECISION, updated DOUBLE PRECISION)""")
            _ready = True
        cur.execute(sql, args)
        rows = [dict(r) for r in cur.fetchall()] if fetch else None
        conn.commit()
        return rows
    finally:
        conn.close()

BASE = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Help Desk</title><style>
body{font:15px/1.5 system-ui,sans-serif;background:#f6f7f9;color:#1b1f24;margin:0}
.w{max-width:820px;margin:0 auto;padding:16px}.c{background:#fff;border:1px solid #e1e4e8;border-radius:10px;padding:16px;margin-bottom:12px}
label{display:block;font-weight:600;margin:10px 0 4px;font-size:13px}
input,select,textarea{width:100%;padding:9px;border:1px solid #cfd4da;border-radius:8px;font:inherit;box-sizing:border-box}
textarea{min-height:120px}button,.b{padding:9px 14px;border:0;border-radius:8px;background:#2563eb;color:#fff;font:inherit;font-weight:600;cursor:pointer;text-decoration:none;display:inline-block}
.m{color:#667085;font-size:13px}.bd{padding:2px 9px;border-radius:99px;font-size:12px;font-weight:600;background:#e5e7eb}
.New{background:#fde68a}.Seen{background:#bfdbfe}.Resolved{background:#bbf7d0}.Closed{background:#d1d5db}.Rejected{background:#fecaca}
.In\\ Progress{background:#fed7aa}.Under\\ Consideration{background:#e9d5ff}
.st{display:flex;gap:8px;margin-bottom:12px}.st div{flex:1;background:#fff;border:1px solid #e1e4e8;border-radius:10px;padding:10px;text-align:center}.st b{display:block;font-size:20px}
a{color:inherit}.row{display:flex;justify-content:space-between;gap:8px}
</style></head><body><div class="w">{{ body|safe }}</div></body></html>"""

def page(body, **kw):
    return render_template_string(BASE, body=render_template_string(body, **kw))

# ---------- Public complaint page ----------
FORM = """<h1>🛠️ Help Desk</h1><div class="c"><b>Tell us what you need help with</b>
<p class="m">Fill in the details and our team will look into it.</p>
{% if err %}<p style="color:#b91c1c">{{err}}</p>{% endif %}
<form method="post"><label>Your name *</label><input name="name" value="{{v.name}}" required>
<label>PC number *</label><input name="pc" value="{{v.pc}}" required>
<label>Describe your problem *</label><textarea name="description" required>{{v.description}}</textarea>
<p><button>Submit request</button></p></form></div>"""
DONE = """<h1>🛠️ Help Desk</h1><div class="c" style="text-align:center"><p>✅ Request received. Your ticket number is</p>
<div style="font-size:28px;font-weight:700;color:#2563eb">{{tid}}</div><p class="m">Our team has been notified.</p>
<a class="b" href="/">Submit another</a></div>"""

@app.route("/", methods=["GET", "POST"])
def complaint():
    v = {"name": "", "pc": "", "description": ""}
    if request.method == "POST":
        v = {k: request.form.get(k, "").strip()[:2000] for k in v}
        if not all(v.values()):
            return page(FORM, v=v, err="Please fill in all fields.")
        tid = "HD-" + secrets.token_hex(3).upper()
        run("INSERT INTO tickets(id,name,pc,description,created,updated) VALUES(?,?,?,?,?,?)",
            (tid, v["name"], v["pc"], v["description"], time.time(), time.time()))
        return page(DONE, tid=tid)
    return page(FORM, v=v, err=None)

# ---------- Staff area ----------
def staff_only():
    if not session.get("staff"): abort(redirect("/staff/login"))

@app.route("/staff/login", methods=["GET", "POST"])
def login():
    err = ""
    if request.method == "POST":
        if secrets.compare_digest(request.form.get("password", ""), STAFF_PASSWORD):
            session["staff"] = True; return redirect("/staff")
        err = "Wrong password."
    return page("""<h1>Staff login</h1><div class="c"><form method="post"><p style="color:#b91c1c">{{err}}</p>
    <label>Password</label><input type="password" name="password" autofocus><p><button>Log in</button></p></form></div>""", err=err)

@app.route("/staff/logout")
def logout():
    session.clear(); return redirect("/staff/login")

DASH = """<meta http-equiv="refresh" content="30"><div class="row"><h1>🛠️ Staff Dashboard</h1><a href="/staff/logout">Log out</a></div>
<div class="st">{% for k,n in stats %}<div><b>{{n}}</b>{{k}}</div>{% endfor %}</div>
<p>{% for s in ["All"]+statuses %}<a href="/staff?s={{s}}" style="margin-right:10px;{{'font-weight:700' if s==cur}}">{{s}}</a>{% endfor %}</p>
{% for t in rows %}<a href="/staff/ticket/{{t.id}}" style="text-decoration:none"><div class="c"><div class="row"><div>
<b>{{t.id}}</b> · PC {{t.pc}} · {{t.name}}<div class="m">{{t.when}}</div><div class="m">{{t.description[:100]}}{{'…' if t.description|length>100}}</div></div>
<span class="bd {{t.status}}">{{t.status}}</span></div></div></a>{% else %}<div class="c m">No requests yet.</div>{% endfor %}"""

@app.route("/staff")
def dashboard():
    staff_only()
    cur = request.args.get("s", "All")
    allt = run("SELECT * FROM tickets ORDER BY created DESC", fetch=True)
    rows = [dict(t, when=time.strftime("%d %b %Y %H:%M", time.localtime(t["created"]))) for t in allt if cur in ("All", t["status"])]
    n = lambda f: sum(1 for t in allt if f(t))
    stats = [("New", n(lambda t: t["status"] == "New")), ("Open", n(lambda t: t["status"] not in ("Resolved", "Closed", "Rejected"))),
             ("Resolved", n(lambda t: t["status"] == "Resolved")), ("Total", len(allt))]
    return page(DASH, rows=rows, stats=stats, statuses=STATUSES, cur=cur)

TICKET = """<p><a href="/staff">← Back</a></p><div class="c"><div class="row"><h2 style="margin:0">{{t.id}}</h2><span class="bd {{t.status}}">{{t.status}}</span></div>
<p class="m">{{t.name}} · PC {{t.pc}} · {{when}}</p><p style="white-space:pre-wrap">{{t.description}}</p>
<form method="post"><label>Status</label><select name="status">{% for s in statuses %}<option {{'selected' if s==t.status}}>{{s}}</option>{% endfor %}</select>
<label>Internal notes (visible to all staff)</label><textarea name="notes">{{t.notes}}</textarea><p><button>Save</button></p></form></div>"""

@app.route("/staff/ticket/<tid>", methods=["GET", "POST"])
def ticket(tid):
    staff_only()
    r = run("SELECT * FROM tickets WHERE id=?", (tid,), fetch=True)
    if not r: abort(404)
    t = r[0]
    if request.method == "POST":
        st = request.form.get("status"); st = st if st in STATUSES else t["status"]
        run("UPDATE tickets SET status=?,notes=?,updated=? WHERE id=?", (st, request.form.get("notes", "")[:5000], time.time(), tid))
        return redirect("/staff")
    if t["status"] == "New":   # auto-mark as Seen
        run("UPDATE tickets SET status='Seen',updated=? WHERE id=?", (time.time(), tid)); t["status"] = "Seen"
    return page(TICKET, t=t, statuses=STATUSES, when=time.strftime("%d %b %Y %H:%M", time.localtime(t["created"])))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
