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
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=Instrument+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{--ink:#0F1B2D;--paper:#EDF0F3;--line:#D9DEE5;--mu:#5B6778;--teal:#0E8F86;--teal2:#0A6B64;--tag:#CFEDE9;
--hd:"Bricolage Grotesque","Trebuchet MS",system-ui,sans-serif;--bd:"Instrument Sans",system-ui,-apple-system,"Segoe UI",sans-serif}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 var(--bd)}
h1,h2,h3{font-family:var(--hd);margin:0;line-height:1.1;letter-spacing:-.02em}
:focus-visible{outline:3px solid var(--teal);outline-offset:2px}
a{color:inherit}
.bar{background:var(--ink);color:#fff;padding:12px 20px;display:flex;align-items:center;gap:14px}
.logo{display:flex;align-items:center;gap:10px;font:800 18px var(--hd);text-decoration:none}
.logo i{background:var(--tag);color:var(--ink);font-style:normal;padding:3px 8px;border-radius:5px 12px 12px 5px;font-size:14px}
.bar .sp{flex:1}.bar .sum{font-size:14px;color:#B8C2D1}.bar .sum b{color:#fff}
.bar a.out{font-size:14px;color:#B8C2D1;text-decoration:none;border:1px solid #33435C;padding:6px 12px;border-radius:8px}
.bar a.out:hover{color:#fff;border-color:#fff}
label{display:block;font-weight:600;font-size:14px;margin:0 0 6px}
input,select,textarea{width:100%;padding:12px 14px;border:1.5px solid var(--line);border-radius:10px;font:inherit;background:#fff;color:var(--ink)}
input:focus,textarea:focus{border-color:var(--teal);outline:0;box-shadow:0 0 0 4px rgba(14,143,134,.15)}
textarea{min-height:120px;resize:vertical}
.btn{display:inline-block;border:0;border-radius:10px;padding:13px 22px;font:600 16px var(--bd);background:var(--teal);color:#fff;cursor:pointer;text-decoration:none;text-align:center}
.btn:hover{background:var(--teal2)}.btn.big{width:100%;padding:16px;font-size:17px}
.btn.alt{background:#fff;color:var(--ink);border:1.5px solid var(--line)}.btn.alt:hover{border-color:var(--ink);background:#fff}
.err{background:#FDECEC;color:#9B1C1C;border-radius:10px;padding:11px 14px;margin-bottom:16px;font-weight:500}
.m{color:var(--mu);font-size:14px}
.pc{display:inline-block;background:var(--tag);color:var(--ink);font:800 13px var(--hd);padding:3px 11px 3px 9px;border-radius:4px 12px 12px 4px;letter-spacing:.02em;white-space:nowrap}

/* ---------- user side ---------- */
.u{max-width:1020px;margin:0 auto;padding:44px 20px 60px;display:grid;grid-template-columns:5fr 6fr;gap:56px;align-items:start}
.u .intro{position:sticky;top:30px}
.u h1{font-size:clamp(34px,5vw,54px)}
.u .lead{font-size:18px;color:var(--mu);margin:18px 0 30px;max-width:30ch}
.track{list-style:none;margin:0;padding:0;border-left:2px solid var(--line)}
.track li{position:relative;padding:0 0 18px 22px}.track li:last-child{padding-bottom:0}
.track li:before{content:"";position:absolute;left:-7px;top:5px;width:12px;height:12px;border-radius:50%;background:var(--paper);border:2px solid #9AA5B5}
.track li.now:before{background:var(--teal);border-color:var(--teal)}
.track b{display:block;font-size:15px}.track span{color:var(--mu);font-size:14px}
.sheet{background:#fff;border-radius:18px;padding:28px;box-shadow:0 1px 0 var(--line),0 24px 48px -28px rgba(15,27,45,.35)}
.sheet h2{font-size:24px;margin-bottom:20px}
.f{margin-bottom:20px}
.tagfield{background:var(--tag);border-radius:8px 22px 22px 8px;padding:14px 18px 16px 22px;position:relative}
.tagfield:before{content:"";position:absolute;left:8px;top:50%;width:8px;height:8px;margin-top:-4px;border-radius:50%;background:var(--paper)}
.tagfield label{margin-left:4px}
.tagfield input{background:#fff;border-color:#9FD6CF;font:800 22px var(--hd);letter-spacing:.03em;border-radius:8px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px}
.chip{border:1.5px solid var(--line);background:#fff;border-radius:99px;padding:6px 13px;font:500 14px var(--bd);cursor:pointer;color:var(--ink)}
.chip:hover{border-color:var(--teal);color:var(--teal2)}
.shotbox{display:flex;align-items:center;gap:14px;border:1.5px dashed #AEB8C6;border-radius:12px;padding:12px;cursor:pointer;margin:0}
.shotbox:hover{border-color:var(--teal);background:#F4FBFA}
.shotbox input{display:none}.shotbox .ic{width:48px;height:48px;border-radius:10px;background:var(--paper);display:grid;place-items:center;font-size:22px;flex:none;overflow:hidden}
.shotbox .ic img{width:100%;height:100%;object-fit:cover}
.shotbox b{display:block;font-size:15px}
.rm{background:none;border:0;color:#9B1C1C;font:500 14px var(--bd);cursor:pointer;padding:6px 0;display:none}
.stub{max-width:560px;margin:0 auto;padding:44px 20px 60px}
.ticket{background:#fff;border-radius:18px;box-shadow:0 24px 48px -28px rgba(15,27,45,.4);position:relative}
.ticket .top{padding:30px 28px 26px}.ticket .top .ok{display:inline-block;background:#DDF3F0;color:var(--teal2);font-weight:600;font-size:14px;padding:4px 12px;border-radius:99px;margin-bottom:14px}
.ticket .no{font:800 clamp(38px,9vw,56px) var(--hd);letter-spacing:-.02em;margin:2px 0 4px}
.perf{border-top:2px dashed var(--line);position:relative;margin:0 22px}
.perf:before,.perf:after{content:"";position:absolute;top:-13px;width:24px;height:24px;border-radius:50%;background:var(--paper)}
.perf:before{left:-34px}.perf:after{right:-34px}
.ticket .bot{padding:24px 28px 30px}.ticket .bot h3{font-size:18px;margin-bottom:16px}

/* ---------- staff side ---------- */
.app{display:grid;grid-template-columns:210px minmax(290px,370px) 1fr;height:calc(100vh - 57px);min-height:480px}
.list{background:#fff;border-right:1px solid var(--line);overflow:auto}
.side{background:#F7F9FB;border-right:1px solid var(--line);padding:18px 12px;overflow:auto}
.side h4{margin:0 10px 10px;font:600 13px var(--bd);color:var(--mu)}
.side a{display:flex;align-items:center;gap:10px;text-decoration:none;font-weight:600;font-size:15px;padding:10px 12px;border-radius:10px;color:var(--ink);margin-bottom:2px}
.side a:hover{background:#E9EEF3}.side a.on{background:var(--ink);color:#fff}
.side a:before{content:"";width:9px;height:9px;border-radius:50%;background:var(--c,#9AA5B5);flex:none}
.side a em{margin-left:auto;font-style:normal;font-size:13px;opacity:.7}
.item{display:block;text-decoration:none;padding:14px 16px 14px 20px;border-bottom:1px solid var(--line);position:relative;border-left:4px solid transparent}
.item:hover{background:#F7F9FB}.item.sel{background:#EAF6F5;border-left-color:var(--teal)}
.item .r1{display:flex;align-items:center;gap:8px}.item .who{font-weight:600;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.item .ago{font-size:12.5px;color:var(--mu);flex:none}
.item p{margin:6px 0 0;font-size:14px;color:var(--mu);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.item.unread .who{font-weight:800}.item.unread:after{content:"";position:absolute;left:7px;top:22px;width:8px;height:8px;border-radius:50%;background:#E8A700}
.s-new{--c:#C98900}.s-seen{--c:#2F6FDB}.s-under-consideration{--c:#7A4FD3}.s-in-progress{--c:#D9600B}.s-resolved{--c:#168A45}.s-closed{--c:#6B7685}.s-rejected{--c:#C42B2B}
.badge{display:inline-flex;align-items:center;gap:6px;font-size:13px;font-weight:600;padding:3px 11px 3px 9px;border-radius:99px;color:var(--c);background:color-mix(in srgb,var(--c) 13%,#fff);white-space:nowrap}
.badge:before{content:"";width:7px;height:7px;border-radius:50%;background:var(--c)}
.detail{overflow:auto;padding:28px 32px 60px}
.detail .in{max-width:680px}
.back{display:none;margin-bottom:14px;font-weight:600;text-decoration:none;color:var(--teal2)}
.dh{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;flex-wrap:wrap}
.dh h2{font-size:30px;margin:10px 0 2px}
.body{background:#fff;border-radius:14px;padding:20px 22px;margin:22px 0;border:1px solid var(--line);font-size:17px;white-space:pre-wrap}
.shot{max-width:100%;border-radius:12px;border:1px solid var(--line);display:block}
.sec{font:600 14px var(--bd);margin:26px 0 10px}
.sbtns{display:flex;flex-wrap:wrap;gap:8px}
.sb{border:1.5px solid var(--line);background:#fff;border-radius:10px;padding:9px 14px;font:600 14px var(--bd);cursor:pointer;color:var(--ink)}
.sb:hover{border-color:var(--c);color:var(--c)}.sb.on{background:var(--c);border-color:var(--c);color:#fff}
.empty{display:grid;place-items:center;height:100%;text-align:center;color:var(--mu);padding:30px}
.empty h3{color:var(--ink);font-size:22px;margin-bottom:8px}
.toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%);background:var(--ink);color:#fff;padding:11px 20px;border-radius:99px;font-weight:600;animation:out 3.2s forwards;z-index:9}
@keyframes out{0%,80%{opacity:1}100%{opacity:0;visibility:hidden}}
.login{max-width:400px;margin:12vh auto;padding:0 20px}.login .sheet{padding:28px}
@media(max-width:860px){
 .u{grid-template-columns:1fr;gap:30px;padding-top:28px}.u .intro{position:static}.u .lead{max-width:none;margin-bottom:22px}
 .track{display:none}.sheet{padding:22px}
 .app{grid-template-columns:1fr;height:auto}.app.has-sel .list,.app.has-sel .side{display:none}.side{border-right:0;border-bottom:1px solid var(--line);padding:12px;display:flex;flex-wrap:wrap;gap:6px}.side h4{display:none}.side a{margin:0;padding:7px 12px;font-size:14px;background:#fff;border:1px solid var(--line)}.side a.on{border-color:var(--ink)}.app:not(.has-sel) .detail{display:none}
 .detail{padding:20px 18px 50px}.back{display:inline-block}.bar .sum{display:none}
}
@media(prefers-reduced-motion:reduce){.toast{animation:none}}
</style></head><body>{{ body|safe }}</body></html>"""

def page(title, body, **kw):
    return render_template_string(BASE, title=title, body=render_template_string(body, **kw))

slug = lambda s: s.lower().replace(" ", "-")
def ago(ts):
    d = max(0, time.time() - ts)
    if d < 60: return "just now"
    if d < 3600: return f"{int(d // 60)} min ago"
    if d < 86400: return f"{int(d // 3600)} h ago"
    return f"{int(d // 86400)} d ago"
fmt = lambda ts: time.strftime("%d %b %Y, %H:%M", time.gmtime(ts)) + " UTC"

# ---------------- Public complaint page ----------------
FORM = """<div class="bar"><a class="logo" href="/"><i>HD</i>Help Desk</a></div>
<main class="u"><div class="intro"><h1>Something wrong with your PC?</h1>
<p class="lead">Tell us what happened. Our team picks it up and fixes it.</p>
</div>
<form class="sheet" method="post"><h2>New request</h2>
{% if err %}<div class="err">{{err}}</div>{% endif %}
<div class="f tagfield"><label for="pc">PC number</label><input id="pc" name="pc" value="{{v.pc}}" placeholder="PC-12" required autocomplete="off"></div>
<div class="f"><label for="nm">Your name</label><input id="nm" name="name" value="{{v.name}}" placeholder="e.g. Ali Khan" required></div>
<div class="f"><label for="ds">What is the problem?</label>

<textarea id="ds" name="description" placeholder="Describe what you see or what happens..." required>{{v.description}}</textarea></div>
<div class="f"><label class="shotbox" for="file"><span class="ic" id="ic">📷</span><span><b id="sb">Add a photo or screenshot</b><span class="m">Optional. It helps us fix things faster.</span></span>
<input type="file" id="file" accept="image/*"></label><button type="button" class="rm" id="rm">Remove photo</button></div>
<input type="hidden" name="image" id="img"><button class="btn big">Send request</button></form></main>
<script>
var file=document.getElementById("file"),img=document.getElementById("img"),ic=document.getElementById("ic"),sb=document.getElementById("sb"),rm=document.getElementById("rm");
file.onchange=function(){var f=file.files[0];if(!f)return;var r=new FileReader();
r.onload=function(e){var im=new Image();im.onload=function(){var s=Math.min(1,1100/Math.max(im.width,im.height)),c=document.createElement("canvas");
c.width=Math.round(im.width*s);c.height=Math.round(im.height*s);c.getContext("2d").drawImage(im,0,0,c.width,c.height);
var u=c.toDataURL("image/jpeg",0.78);img.value=u;ic.innerHTML='<img alt="" src="'+u+'">';sb.textContent="Photo added";rm.style.display="block";};im.src=e.target.result;};
r.readAsDataURL(f);};
rm.onclick=function(){img.value="";file.value="";ic.textContent="📷";sb.textContent="Add a photo or screenshot";rm.style.display="none";};
</script>"""

DONE = """<div class="bar"><a class="logo" href="/"><i>HD</i>Help Desk</a></div>
<main class="stub"><div class="ticket"><div class="top"><span class="ok">Request sent</span>
<div class="m">Your ticket number</div><div class="no">{{tid}}</div><span class="pc">{{pc}}</span> <span class="m">&nbsp;{{name}}</span></div>
<div class="perf"></div><div class="bot"><h3>What happens next</h3>
<ul class="track"><li class="now"><b>Request received</b><span>Our team has been notified</span></li>
<li><b>We open it</b><span>Your request is marked as seen</span></li><li><b>We fix it</b><span>Keep your ticket number if you need to ask about it</span></li></ul>
<p style="margin:26px 0 0"><a class="btn alt" href="/">Send another request</a></p></div></div></main>"""

@app.route("/", methods=["GET", "POST"])
def complaint():
    v = {"name": "", "pc": "", "description": ""}
    if request.method == "POST":
        v = {k: request.form.get(k, "").strip()[:2000] for k in v}
        if not all(v.values()):
            return page("Help Desk", FORM, v=v, err="Add your PC number, your name and a short description of the problem.")
        img = request.form.get("image", "")
        if not (img.startswith("data:image/jpeg;base64,") and len(img) <= MAX_IMG):
            img = ""
        tid = "HD-" + secrets.token_hex(3).upper()
        run("INSERT INTO tickets(id,name,pc,description,image,created,updated) VALUES(?,?,?,?,?,?,?)",
            (tid, v["name"], v["pc"], v["description"], img or None, time.time(), time.time()))
        return page("Request sent", DONE, tid=tid, pc=v["pc"], name=v["name"])
    return page("Help Desk", FORM, v=v, err=None)

# ---------------- Staff area ----------------
def staff_only():
    if not session.get("staff"): abort(redirect("/staff/login"))

LOGIN = """<div class="login"><a class="logo" href="/staff" style="color:var(--ink);margin-bottom:18px"><i>HD</i>Help Desk team</a>
<form class="sheet" method="post"><h2>Log in</h2>{% if err %}<div class="err">{{err}}</div>{% endif %}
<div class="f"><label for="pw">Team password</label><input id="pw" type="password" name="password" autofocus></div>
<button class="btn big">Open dashboard</button></form></div>"""

@app.route("/staff/login", methods=["GET", "POST"])
def login():
    err = ""
    if request.method == "POST":
        if secrets.compare_digest(request.form.get("password", ""), STAFF_PASSWORD):
            session["staff"] = True; return redirect("/staff")
        err = "That password is not correct. Try again."
    return page("Staff login", LOGIN, err=err)

@app.route("/staff/logout")
def logout():
    session.clear(); return redirect("/staff/login")

DASH = """<div class="bar"><a class="logo" href="/staff"><i>HD</i>Help Desk</a><span class="sp"></span>
<span class="sum"><b>{{counts['New']}}</b> new &nbsp;·&nbsp; <b>{{open_n}}</b> open</span><a class="out" href="/staff/logout">Log out</a></div>
<div class="app {{'has-sel' if sel}}">
<nav class="side"><h4>Requests</h4>{% for s in ["All"]+statuses %}<a href="/staff?s={{s}}" class="{{'on' if s==cur}} {{'s-'+(s|lower|replace(' ','-')) if s!='All'}}">{{s}}<em>{{total if s=='All' else counts[s]}}</em></a>{% endfor %}</nav>
<aside class="list">
{% for t in rows %}<a class="item s-{{t.slug}} {{'sel' if sel and sel.id==t.id}} {{'unread' if t.status=='New'}}" href="/staff?s={{cur}}&t={{t.id}}">
<div class="r1"><span class="pc">{{t.pc}}</span><span class="who">{{t.name}}</span>{% if t.has_image %}<span title="Has photo">📷</span>{% endif %}<span class="ago">{{t.ago}}</span></div>
<p>{{t.description}}</p></a>
{% else %}<div class="empty"><div><h3>Nothing here</h3>{{'New requests appear here as soon as someone sends the form.' if total==0 else 'No requests with this status.'}}</div></div>{% endfor %}</aside>
<section class="detail">{% if sel %}<div class="in"><a class="back" href="/staff?s={{cur}}">← All requests</a>
<div class="dh"><div><span class="pc" style="font-size:16px">{{sel.pc}}</span><h2>{{sel.name}}</h2><div class="m">{{sel.id}} · {{when}}</div></div>
<span class="badge s-{{sslug}}">{{sel.status}}</span></div>
<div class="body">{{sel.description}}</div>
{% if sel.image %}<a href="{{sel.image}}" target="_blank"><img class="shot" src="{{sel.image}}" alt="Photo from the user"></a>{% endif %}
<form method="post" action="/staff/ticket/{{sel.id}}?s={{cur}}"><div class="sec">Set status</div>
<div class="sbtns">{% for s in statuses %}<button name="status" value="{{s}}" class="sb s-{{s|lower|replace(' ','-')}} {{'on' if s==sel.status}}">{{s}}</button>{% endfor %}</div>
<div class="sec">Team notes <span class="m">(only staff can see these)</span></div>
<textarea name="notes" id="notes" placeholder="What did you check? What is left to do?">{{sel.notes}}</textarea>
<p><button name="status" value="{{sel.status}}" class="btn">Save notes</button></p></form></div>
{% else %}<div class="empty"><div><h3>Pick a request</h3>Select one on the left. It is marked as seen when you open it.</div></div>{% endif %}</section></div>
{% if saved %}<div class="toast">Changes saved</div>{% endif %}
<script>var n=document.getElementById("notes"),o=n?n.value:"";
setInterval(function(){if(document.hidden)return;if(n&&(n.value!==o||document.activeElement===n))return;location.reload();},30000);</script>"""

@app.route("/staff")
def dashboard():
    staff_only()
    cur = request.args.get("s", "All"); tid = request.args.get("t", ""); sel = None
    if tid:
        r = run("SELECT * FROM tickets WHERE id=?", (tid,), fetch=True)
        if r:
            sel = r[0]
            if sel["status"] == "New":
                run("UPDATE tickets SET status='Seen',updated=? WHERE id=?", (time.time(), tid)); sel["status"] = "Seen"
    allt = run("""SELECT id,name,pc,description,status,created,
                  (image IS NOT NULL AND image <> '') AS has_image FROM tickets ORDER BY created DESC""", fetch=True)
    counts = {s: 0 for s in STATUSES}
    for t in allt: counts[t["status"]] = counts.get(t["status"], 0) + 1
    rows = [dict(t, ago=ago(t["created"]), slug=slug(t["status"])) for t in allt if cur in ("All", t["status"])]
    open_n = sum(v for k, v in counts.items() if k not in ("Resolved", "Closed", "Rejected"))
    return page("Staff dashboard", DASH, rows=rows, counts=counts, total=len(allt), open_n=open_n, statuses=STATUSES,
                cur=cur, sel=sel, when=fmt(sel["created"]) if sel else "", sslug=slug(sel["status"]) if sel else "",
                saved=request.args.get("saved"))

@app.route("/staff/ticket/<tid>", methods=["GET", "POST"])
def ticket(tid):
    staff_only()
    cur = request.args.get("s", "All")
    if request.method == "POST":
        st = request.form.get("status")
        if st in STATUSES:
            run("UPDATE tickets SET status=?,notes=?,updated=? WHERE id=?", (st, request.form.get("notes", "")[:5000], time.time(), tid))
        return redirect(f"/staff?s={cur}&t={tid}&saved=1")
    return redirect(f"/staff?s={cur}&t={tid}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
