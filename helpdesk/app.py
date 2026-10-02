import os, secrets, time
from flask import Flask, request, redirect, session, render_template_string, abort

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
STAFF_PASSWORD = os.environ.get("STAFF_PASSWORD", "changeme")
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
STATUSES = ["New", "Seen", "Under Consideration", "In Progress", "Resolved", "Closed", "Rejected"]
MAX_IMG = 1_500_000  # characters (~1.1 MB) after the browser has shrunk the photo
_ready = False

def run(sql, args=(), fetch=False):
    """Postgres on Vercel (DATABASE_URL set), SQLite for local testing."""
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
            try:  # add the photo column to an existing table
                if DATABASE_URL: cur.execute("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS image TEXT")
                else: cur.execute("ALTER TABLE tickets ADD COLUMN image TEXT")
            except Exception:
                conn.rollback()
            conn.commit(); _ready = True
        cur.execute(sql, args)
        rows = [dict(r) for r in cur.fetchall()] if fetch else None
        conn.commit()
        return rows
    finally:
        conn.close()

BASE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{{title}}</title>
<style>
:root{--ac:#4f46e5;--ac2:#7c3aed;--bg:#f3f4fb;--tx:#1e1b3a;--mu:#6b7280;--bd:#e5e7f0}
*{box-sizing:border-box}
body{margin:0;font:15px/1.55 -apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--tx)}
.top{background:linear-gradient(135deg,var(--ac),var(--ac2));color:#fff;padding:22px 16px 60px}
.top .in{max-width:880px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;gap:10px}
.top h1{margin:0;font-size:22px}.top p{margin:2px 0 0;opacity:.85;font-size:14px}
.top a{color:#fff;opacity:.9;text-decoration:none;font-weight:600;font-size:14px;background:rgba(255,255,255,.18);padding:7px 13px;border-radius:99px}
.w{max-width:880px;margin:-40px auto 40px;padding:0 16px}
.c{background:#fff;border:1px solid var(--bd);border-radius:16px;padding:22px;margin-bottom:14px;box-shadow:0 6px 24px rgba(79,70,229,.07)}
label{display:block;font-weight:600;margin:14px 0 6px;font-size:13.5px}
input,select,textarea{width:100%;padding:11px 13px;border:1.5px solid var(--bd);border-radius:10px;font:inherit;background:#fbfbfe;color:var(--tx)}
input:focus,select:focus,textarea:focus{outline:0;border-color:var(--ac);box-shadow:0 0 0 3px rgba(79,70,229,.15)}
textarea{min-height:130px;resize:vertical}
button,.btn{display:inline-block;padding:12px 22px;border:0;border-radius:10px;background:linear-gradient(135deg,var(--ac),var(--ac2));color:#fff;font:inherit;font-weight:700;cursor:pointer;text-decoration:none}
button:hover,.btn:hover{filter:brightness(1.07)}
.ghost{background:#eef0fb;color:var(--ac)}
.m{color:var(--mu);font-size:13px}.err{background:#fef2f2;color:#b91c1c;padding:10px 13px;border-radius:10px;margin:12px 0}
.up{border:2px dashed #c7cae8;border-radius:12px;padding:16px;text-align:center;background:#fbfbfe;cursor:pointer;display:block;color:var(--mu);font-weight:500;margin:0}
.up:hover{border-color:var(--ac)}.up input{display:none}
#pv{display:none;max-width:100%;max-height:220px;border-radius:10px;margin-top:10px;border:1px solid var(--bd)}
.done{text-align:center;padding:30px 20px}.tick{font-size:46px}.tid{font-size:32px;font-weight:800;color:var(--ac);letter-spacing:1px;margin:6px 0}
.st{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:14px}
.st div{background:#fff;border:1px solid var(--bd);border-radius:14px;padding:14px;text-align:center;box-shadow:0 4px 14px rgba(79,70,229,.06)}
.st b{display:block;font-size:26px;color:var(--ac)}.st span{color:var(--mu);font-size:12.5px;font-weight:600}
.pills{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:14px}
.pills a{padding:6px 13px;border-radius:99px;background:#fff;border:1px solid var(--bd);text-decoration:none;color:var(--tx);font-size:13px;font-weight:600}
.pills a.on{background:var(--ac);color:#fff;border-color:var(--ac)}
.tk{display:block;text-decoration:none;color:inherit;border-left:5px solid var(--ac);padding:16px 18px}
.tk:hover{transform:translateY(-1px);box-shadow:0 8px 26px rgba(79,70,229,.14)}
.row{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}
.bd{padding:3px 11px;border-radius:99px;font-size:12px;font-weight:700;white-space:nowrap}
.s-new{background:#fef3c7;color:#92400e}.s-seen{background:#dbeafe;color:#1e40af}
.s-under-consideration{background:#ede9fe;color:#5b21b6}.s-in-progress{background:#ffedd5;color:#9a3412}
.s-resolved{background:#dcfce7;color:#166534}.s-closed{background:#e5e7eb;color:#374151}.s-rejected{background:#fee2e2;color:#991b1b}
.shot{max-width:100%;border-radius:12px;border:1px solid var(--bd);margin:6px 0 4px}
.tk.s-new{border-left-color:#f59e0b}.tk.s-seen{border-left-color:#3b82f6}.tk.s-under-consideration{border-left-color:#8b5cf6}
.tk.s-in-progress{border-left-color:#f97316}.tk.s-resolved{border-left-color:#22c55e}.tk.s-closed{border-left-color:#9ca3af}.tk.s-rejected{border-left-color:#ef4444}
@media(max-width:560px){.st{grid-template-columns:repeat(2,1fr)}.top h1{font-size:19px}}
</style></head><body>{{ body|safe }}</body></html>"""

def page(title, body, **kw):
    return render_template_string(BASE, title=title, body=render_template_string(body, **kw))

# ---------------- Public complaint page ----------------
FORM = """<div class="top"><div class="in"><div><h1>🛠️ Help Desk</h1><p>Report a problem and our team will get to it.</p></div></div></div>
<div class="w"><div class="c">
<b style="font-size:17px">Submit a request</b>
{% if err %}<div class="err">{{err}}</div>{% endif %}
<form method="post" id="f">
<label>Your name *</label><input name="name" value="{{v.name}}" placeholder="e.g. Ali Khan" required>
<label>PC number *</label><input name="pc" value="{{v.pc}}" placeholder="e.g. PC-12" required>
<label>Describe your problem *</label><textarea name="description" placeholder="Tell us what is happening..." required>{{v.description}}</textarea>
<label>Photo (optional)</label>
<label class="up" for="file">📷 Tap to add a photo or screenshot<input type="file" id="file" accept="image/*"></label>
<img id="pv" alt="preview"><p><button type="button" class="ghost" id="rm" style="display:none;padding:7px 14px">Remove photo</button></p>
<input type="hidden" name="image" id="img">
<p><button>Submit request</button></p></form></div></div>
<script>
var file=document.getElementById("file"),pv=document.getElementById("pv"),img=document.getElementById("img"),rm=document.getElementById("rm");
file.onchange=function(){var f=file.files[0];if(!f)return;var r=new FileReader();
r.onload=function(e){var im=new Image();im.onload=function(){
var s=Math.min(1,1100/Math.max(im.width,im.height)),c=document.createElement("canvas");
c.width=Math.round(im.width*s);c.height=Math.round(im.height*s);c.getContext("2d").drawImage(im,0,0,c.width,c.height);
var d=c.toDataURL("image/jpeg",0.78);img.value=d;pv.src=d;pv.style.display="block";rm.style.display="inline-block";};im.src=e.target.result;};
r.readAsDataURL(f);};
rm.onclick=function(){img.value="";file.value="";pv.style.display="none";rm.style.display="none";};
</script>"""

DONE = """<div class="top"><div class="in"><div><h1>🛠️ Help Desk</h1></div></div></div>
<div class="w"><div class="c done"><div class="tick">✅</div><b style="font-size:18px">Request received</b>
<p class="m">Your ticket number is</p><div class="tid">{{tid}}</div>
<p class="m">Please keep this number. Our team has been notified.</p><a class="btn" href="/">Submit another request</a></div></div>"""

@app.route("/", methods=["GET", "POST"])
def complaint():
    v = {"name": "", "pc": "", "description": ""}
    if request.method == "POST":
        v = {k: request.form.get(k, "").strip()[:2000] for k in v}
        if not all(v.values()):
            return page("Help Desk", FORM, v=v, err="Please fill in your name, PC number and problem.")
        img = request.form.get("image", "")
        if not (img.startswith("data:image/jpeg;base64,") and len(img) <= MAX_IMG):
            img = ""
        tid = "HD-" + secrets.token_hex(3).upper()
        run("INSERT INTO tickets(id,name,pc,description,image,created,updated) VALUES(?,?,?,?,?,?,?)",
            (tid, v["name"], v["pc"], v["description"], img or None, time.time(), time.time()))
        return page("Request received", DONE, tid=tid)
    return page("Help Desk", FORM, v=v, err=None)

# ---------------- Staff area ----------------
def staff_only():
    if not session.get("staff"): abort(redirect("/staff/login"))

LOGIN = """<div class="top"><div class="in"><div><h1>🔒 Staff login</h1><p>Help Desk team only</p></div></div></div>
<div class="w"><div class="c" style="max-width:420px;margin:0 auto"><form method="post">
{% if err %}<div class="err">{{err}}</div>{% endif %}
<label style="margin-top:0">Password</label><input type="password" name="password" autofocus>
<p><button style="width:100%">Log in</button></p></form></div></div>"""

@app.route("/staff/login", methods=["GET", "POST"])
def login():
    err = ""
    if request.method == "POST":
        if secrets.compare_digest(request.form.get("password", ""), STAFF_PASSWORD):
            session["staff"] = True; return redirect("/staff")
        err = "Wrong password."
    return page("Staff login", LOGIN, err=err)

@app.route("/staff/logout")
def logout():
    session.clear(); return redirect("/staff/login")

DASH = """<meta http-equiv="refresh" content="30">
<div class="top"><div class="in"><div><h1>🛠️ Staff Dashboard</h1><p>New complaints appear at the top</p></div><a href="/staff/logout">Log out</a></div></div>
<div class="w"><div class="st">{% for k,n in stats %}<div><b>{{n}}</b><span>{{k}}</span></div>{% endfor %}</div>
<div class="pills">{% for s in ["All"]+statuses %}<a href="/staff?s={{s}}" class="{{'on' if s==cur}}">{{s}}</a>{% endfor %}</div>
{% for t in rows %}<a class="c tk s-{{t.slug}}" href="/staff/ticket/{{t.id}}"><div class="row"><div>
<b>{{t.id}}</b> · PC {{t.pc}} · {{t.name}} {% if t.has_image %}📷{% endif %}
<div class="m">{{t.when}}</div><div style="margin-top:5px">{{t.description[:110]}}{{'…' if t.description|length>110}}</div></div>
<span class="bd s-{{t.slug}}">{{t.status}}</span></div></a>
{% else %}<div class="c m" style="text-align:center">No requests here yet.</div>{% endfor %}</div>"""

slug = lambda s: s.lower().replace(" ", "-")
fmt = lambda ts: time.strftime("%d %b %Y, %H:%M", time.gmtime(ts)) + " UTC"

@app.route("/staff")
def dashboard():
    staff_only()
    cur = request.args.get("s", "All")
    allt = run("""SELECT id,name,pc,description,status,notes,created,
                  (image IS NOT NULL AND image <> '') AS has_image FROM tickets ORDER BY created DESC""", fetch=True)
    rows = [dict(t, when=fmt(t["created"]), slug=slug(t["status"])) for t in allt if cur in ("All", t["status"])]
    n = lambda f: sum(1 for t in allt if f(t))
    stats = [("New", n(lambda t: t["status"] == "New")),
             ("Open", n(lambda t: t["status"] not in ("Resolved", "Closed", "Rejected"))),
             ("Resolved", n(lambda t: t["status"] == "Resolved")), ("Total", len(allt))]
    return page("Staff Dashboard", DASH, rows=rows, stats=stats, statuses=STATUSES, cur=cur)

TICKET = """<div class="top"><div class="in"><div><h1>{{t.id}}</h1><p>PC {{t.pc}} · {{t.name}}</p></div><a href="/staff">← Back</a></div></div>
<div class="w"><div class="c"><div class="row"><span class="m">{{when}}</span><span class="bd s-{{slug}}">{{t.status}}</span></div>
<p style="white-space:pre-wrap;font-size:16px">{{t.description}}</p>
{% if t.image %}<a href="{{t.image}}" target="_blank"><img class="shot" src="{{t.image}}" alt="attached photo"></a><div class="m">Tap the photo to open it full size</div>{% endif %}
<form method="post"><label>Status</label><select name="status">{% for s in statuses %}<option {{'selected' if s==t.status}}>{{s}}</option>{% endfor %}</select>
<label>Internal notes (visible to all staff, not to users)</label><textarea name="notes">{{t.notes}}</textarea>
<p><button>Save changes</button></p></form></div></div>"""

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
    if t["status"] == "New":
        run("UPDATE tickets SET status='Seen',updated=? WHERE id=?", (time.time(), tid)); t["status"] = "Seen"
    return page(tid, TICKET, t=t, statuses=STATUSES, when=fmt(t["created"]), slug=slug(t["status"]))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
