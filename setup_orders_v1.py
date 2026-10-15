#!/usr/bin/env python3
# 1) /orders - "My orders & payments": what is active, what is waiting, every payment with receipt and method.
# 2) Receipts name the right payment method (JazzCash, Google Play) instead of "test".
# 3) Company register (platform earnings) counts JazzCash and Google Play as real income, and adds Google's 15% fee as an expense.
# 4) Google Play licence-test purchases are marked as test (not counted as income).
#   python3 /root/setup_orders_v1.py            dry run
#   python3 /root/setup_orders_v1.py --apply    install (backup in /root/orders_bak_<time>)
import json, os, re, shutil, subprocess, sys, time
from datetime import datetime

API = "/var/www/xpertcreation-api"
LAND = "/var/www/xpertcreation-landing"
NGINX = "/etc/nginx/sites-enabled/xpertcreation-landing"
APPLY = "--apply" in sys.argv
BODY = '<div class="wrap" style="max-width:820px">\n<style>\n.mo h1{font-size:26px;margin:0 0 4px}.mo .s{color:#5A657C;font-size:14.5px;margin:0 0 14px}\n.mo-sum{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:14px}\n.mo-sum div{background:#fff;border:1px solid #E4E8F2;border-radius:16px;padding:12px;font-size:12px;color:#5A657C}\n.mo-sum b{display:block;font-size:20px;color:#0D1424;font-weight:900;letter-spacing:-.02em}\n.mo-h{display:flex;align-items:center;justify-content:space-between;margin:18px 0 8px}.mo-h h2{font-size:17px;margin:0}.mo-h a{font-size:13px;font-weight:800;color:#1B4DFF;text-decoration:none}\n.mo-c{background:#fff;border:1px solid #E4E8F2;border-radius:16px;padding:12px 14px;margin-bottom:8px;display:flex;gap:12px;align-items:center}\n.mo-c .ic{width:42px;height:42px;border-radius:12px;display:grid;place-items:center;font-size:20px;background:#EEF2FF;flex:0 0 auto}\n.mo-c .t{flex:1;min-width:0;font-size:12.5px;color:#5A657C}.mo-c .t b{display:block;font-size:15px;color:#0D1424}\n.mo-c .r{text-align:right;font-size:12px;color:#5A657C;flex:0 0 auto}.mo-c .r b{display:block;font-size:15px;color:#0D1424}\n.mo-bar{height:6px;border-radius:99px;background:#EEF2F7;margin-top:6px;overflow:hidden}.mo-bar i{display:block;height:100%;background:linear-gradient(90deg,#1B4DFF,#7C3AED)}\n.mo-st{display:inline-block;font-size:11px;font-weight:800;padding:3px 8px;border-radius:99px;margin-top:4px}\n.mo-st.live{background:#DCFCE7;color:#166534}.mo-st.pend{background:#FEF3C7;color:#92400E}.mo-st.off{background:#F1F5F9;color:#475569}.mo-st.ref{background:#FEE2E2;color:#991B1B}\n.mo-pm{display:inline-block;font-size:11px;font-weight:700;padding:3px 8px;border-radius:99px;background:#F1F5F9;color:#334155;margin:4px 0 0 4px}\n.mo-c a.rc{font-weight:800;color:#1B4DFF;text-decoration:none;font-size:12.5px}\n.mo-e{background:#fff;border:1px dashed #CBD5E1;border-radius:16px;padding:20px;text-align:center;color:#5A657C;font-size:14px}\n.mo-more{display:grid;grid-template-columns:1fr 1fr;gap:8px}.mo-more a{display:block;background:#fff;border:1px solid #E4E8F2;border-radius:14px;padding:12px;color:#0D1424;text-decoration:none;font-weight:800;font-size:14px}.mo-more small{display:block;font-weight:500;color:#5A657C;font-size:12px}\n@media(max-width:520px){.mo-sum{grid-template-columns:1fr 1fr}.mo-sum div:last-child{grid-column:1/-1}}\n</style>\n<div class="mo">\n<h1>&#129534; My orders &amp; payments</h1>\n<p class="s">Everything you have bought on XpertCreation: what is active now, what is waiting for payment, and every payment with its receipt.</p>\n<div id="mobox"><div class="mo-e">Loading…</div></div>\n</div>\n<script>\n(function(){\n  "use strict";\n  var ICON = {profile_boost: "🚀", post_boost: "📣", featured_job: "💼", company_pro: "🏢", blue_tick: "✔️",\n    gig_boost: "⭐", property_boost: "🏠", product_boost: "🛍️", merchant_gold: "🥇", merchant_platinum: "💎"};\n  var PM = {"safepay-production": "Card / wallet (Safepay)", "safepay-sandbox": "Safepay test", "jazzcash": "JazzCash / Raast",\n    "googleplay": "Google Play", "googleplay-test": "Google Play test", "demo": "Demo", "test": "Test", "": "–"};\n  var REAL = {"safepay-production": 1, "jazzcash": 1, "googleplay": 1};\n  function esc(s){ return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }\n  function rs(n){ return "Rs " + Number(n || 0).toLocaleString("en-PK"); }\n  function day(t){ return t ? new Date(t).toLocaleDateString("en-GB", {day: "numeric", month: "short", year: "numeric"}) : ""; }\n  function pm(p){ return PM[p] != null ? PM[p] : (/^safepay/.test(p) ? "Safepay" : p); }\n  var box = document.getElementById("mobox");\n  fetch("/api/shop/", {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; }).then(function(d){\n    if (!d){ box.innerHTML = \'<div class="mo-e">Could not load your orders. Please try again.</div>\'; return; }\n    var all = d.orders || [];\n    if (!d.orders){ box.innerHTML = \'<div class="mo-e"><a href="/login?next=/orders" style="font-weight:800">Sign in</a> to see your orders and payments.</div>\'; return; }\n    var now = Date.now();\n    var live = all.filter(function(o){ return o.status === "paid" && (!o.ends || new Date(o.ends).getTime() > now); });\n    var pend = all.filter(function(o){ return o.status === "pending"; });\n    var paid = all.filter(function(o){ return o.status === "paid" || o.status === "refunded"; });\n    var spent = paid.filter(function(o){ return o.status === "paid" && REAL[o.provider]; }).reduce(function(a, o){ return a + (o.amount || 0); }, 0);\n    var h = \'<div class="mo-sum"><div>Active now<b>\' + live.length + \'</b></div><div>Waiting for payment<b>\' + pend.length + \'</b></div><div>Total paid<b>\' + rs(spent) + \'</b></div></div>\';\n    h += \'<div class="mo-h"><h2>✅ Active now</h2><a href="/promote">Buy more →</a></div>\';\n    h += live.length ? live.map(function(o){\n      var pct = 0, left = "";\n      if (o.starts && o.ends){ var st = new Date(o.starts).getTime(), en = new Date(o.ends).getTime(); pct = Math.max(2, Math.min(100, Math.round((now - st) / (en - st) * 100))); var dl = Math.max(0, Math.ceil((en - now) / 864e5)); left = dl + (dl === 1 ? " day" : " days") + " left · until " + day(o.ends); }\n      else left = "No end date";\n      return \'<div class="mo-c"><span class="ic">\' + (ICON[o.product] || "⭐") + \'</span><div class="t"><b>\' + esc(o.name) + \' · \' + esc(o.plan) + \'</b>\' + (o.for ? esc(o.for) + \' · \' : \'\') + left\n        + (pct ? \'<div class="mo-bar"><i style="width:\' + pct + \'%"></i></div>\' : \'\') + \'</div><div class="r"><span class="mo-st live">Active</span></div></div>\';\n    }).join("") : \'<div class="mo-e">Nothing active right now. <a href="/promote" style="font-weight:800">See boosts and plans</a></div>\';\n    if (pend.length){\n      h += \'<div class="mo-h"><h2>⏳ Waiting for payment</h2><a href="/promote#pmorders">Pay or cancel →</a></div>\';\n      h += pend.map(function(o){ return \'<div class="mo-c"><span class="ic">\' + (ICON[o.product] || "⭐") + \'</span><div class="t"><b>\' + esc(o.name) + \' · \' + esc(o.plan) + \'</b>Ordered \' + day(o.created) + (o.for ? \' · \' + esc(o.for) : \'\') + \'</div><div class="r"><b>\' + rs(o.amount) + \'</b><span class="mo-st pend">Waiting</span></div></div>\'; }).join("");\n    }\n    h += \'<div class="mo-h"><h2>💳 All payments</h2></div>\';\n    h += paid.length ? paid.map(function(o){\n      var ended = o.status === "paid" && o.ends && new Date(o.ends).getTime() <= now;\n      var st = o.status === "refunded" ? \'<span class="mo-st ref">Refunded</span>\' : (ended ? \'<span class="mo-st off">Ended</span>\' : \'<span class="mo-st live">Active</span>\');\n      return \'<div class="mo-c"><span class="ic">\' + (ICON[o.product] || "⭐") + \'</span><div class="t"><b>\' + esc(o.name) + \' · \' + esc(o.plan) + \'</b>\' + day(o.created) + \' · order XC-\' + ("00000" + o.id).slice(-6)\n        + \'<br><span class="mo-pm">\' + esc(pm(o.provider)) + \'</span>\' + st + \'</div><div class="r"><b>\' + rs(o.amount) + \'</b><a class="rc" href="/receipt?order=\' + o.id + \'">Receipt</a></div></div>\';\n    }).join("") : \'<div class="mo-e">No payments yet.</div>\';\n    h += \'<div class="mo-h"><h2>Other orders</h2></div><div class="mo-more"><a href="/market">🧑\u200d💻 Freelance<small>Services you bought or sold</small></a><a href="/store">🛒 Store<small>Products you ordered</small></a></div>\';\n    box.innerHTML = h;\n  }).catch(function(){ box.innerHTML = \'<div class="mo-e">Network problem. Please try again.</div>\'; });\n})();\n</script>\n'
SHOP_ADD = """

# ---- setup_orders_v1: receipts show the real payment method for JazzCash and Google Play.
_receipt_data_v5 = _receipt_data


def _receipt_data(o):
    d = _receipt_data_v5(o)
    if o.provider == "jazzcash":
        d["method"], d["test"] = "JazzCash / Raast (checked by our team)", False
    elif o.provider == "googleplay":
        d["method"], d["test"], d["reference"] = "Google Play", False, o.provider_ref
    elif o.provider == "googleplay-test":
        d["method"], d["test"] = "Google Play test purchase (no money taken)", True
    return d
"""
PB_A = '        o.provider_ref = (data.get("orderId") or "")[:120]\n        o.save(update_fields=["provider_ref"])\n'
PB_B = ('        o.provider_ref = (data.get("orderId") or "")[:120]\n'
        '        o.provider = "googleplay-test" if str(data.get("purchaseType", "")) == "0" else "googleplay"   # setup_orders_v1: 0 = licence test\n'
        '        o.save(update_fields=["provider_ref", "provider"])\n')
CB = [('REAL = "safepay-production"\n', 'REAL = "safepay-production"\nREALS = ("safepay-production", "jazzcash", "googleplay")   # setup_orders_v1\n'),
      ('            t = o.provider != REAL\n', '            t = o.provider not in REALS\n'),
      ('                 note="%s (%s), order %d" % (name, o.plan, o.id), test=t)\n',
       '                 note="%s (%s), order %d" % (name, o.plan, o.id), test=t)\n'
       '            if o.provider == "googleplay":\n'
       '                _put("gpfee:%d" % o.id, day=_d(o.paid_at), kind="expense", source="shop", category="Payment gateway fees",\n'
       '                     amount=int(round(o.amount * 0.15)), note="Google Play fee (15 percent), order %d" % o.id, test=False)\n')]
PR_A = """'<div class="pm-sh" id="pmorders"><h2>Your orders</h2><span>'"""
PR_B = """'<div class="pm-sh" id="pmorders"><h2>Your orders</h2><a href="/orders" style="font-weight:800;font-size:13px;color:#1B4DFF;text-decoration:none;margin-left:auto;margin-right:10px">All orders &amp; payments \\u2192</a><span>'"""
FIX = r"""
from companybook.models import Entry
from shop.models import Order
REALS = ("safepay-production", "jazzcash", "googleplay")
try:
    import companybook.views as CV; CV.sync()
except Exception as e:
    print("XCFIX sync skipped", e.__class__.__name__)
n = 0
for e in Entry.objects.filter(ref__startswith="shop", test=True):
    try:
        oid = int(e.ref.split(":")[1])
    except Exception:
        continue
    o = Order.objects.filter(pk=oid).only("provider").first()
    if o and o.provider in REALS:
        e.test = False; e.save(update_fields=["test"]); n += 1
print("XCFIX", n)
"""
ENTRY = {"icon": "\U0001F9FE", "title": "My orders & payments", "link": "/orders",
         "text": "One page with everything you bought: what is active now and how many days are left, orders waiting for payment, and every payment with its method (card, JazzCash or Google Play) and receipt.",
         "how": ["Open xpertcreation.com/orders, or Promote -> All orders & payments.", "Tap Receipt on any payment to view or download it."]}


def bye(c):
    os.chdir("/root"); sys.exit(c)


def sh(c, t=300):
    r = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=t)
    return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()


def code(p):
    return sh("curl -sk -o /dev/null -w '%%{http_code}' -H 'Host: xpertcreation.com' 'https://127.0.0.1%s'" % p)[1]


py = next((p for p in (API + "/venv/bin/python", API + "/.venv/bin/python", API + "/env/bin/python") if os.path.exists(p)), "python3")
SV, PBV, CBV = API + "/shop/views.py", API + "/playbill/views.py", API + "/companybook/views.py"
SHELL, PR, OUT = LAND + "/terms-of-sale.html", LAND + "/promote.html", LAND + "/orders.html"
sv, cb, shell, pr, ng = [open(p, encoding="utf-8").read() for p in (SV, CBV, SHELL, PR, NGINX)]
pb = open(PBV, encoding="utf-8").read() if os.path.exists(PBV) else ""
print("== Checks")
bad = False
def chk(label, done, ok):
    global bad
    print("  %-40s %s" % (label, "already done" if done else ("ok" if ok else "NOT FOUND")))
    if not done and not ok: bad = True
chk("shop/views.py: receipt method", "setup_orders_v1" in sv, "def _receipt_data(o):" in sv)
chk("playbill/views.py: test purchases", "setup_orders_v1" in pb, pb.count(PB_A) == 1)
for i, (a, b) in enumerate(CB):
    chk("companybook/views.py: part %d" % (i + 1), "setup_orders_v1" in cb and i == 0 or (i > 0 and b in cb), cb.count(a) == 1)
chk("promote.html: link to /orders", "/orders" in pr, pr.count(PR_A) == 1)
W0 = '<div class="wrap" style="max-width:760px">'
i0 = shell.find(W0); i1 = shell.find("\n</div>\n", i0)
chk("page shell (terms-of-sale.html)", False, i0 > 0 and i1 > i0)
i_ng = ng.find("    location = /tools "); j_ng = ng.find("listen 80;")
chk("nginx anchor in the 443 block", "location = /orders " in ng, i_ng != -1 and (j_ng == -1 or i_ng < j_ng))
page = None
if i0 > 0 and i1 > i0:
    page = shell[:i0] + BODY.rstrip("\n") + shell[i1:]
    for a, b in (("Terms of sale \u2014 XpertCreation", "My orders & payments \u2014 XpertCreation"),
                 ("https://xpertcreation.com/terms-of-sale", "https://xpertcreation.com/orders"),
                 ("Terms for buying paid items on XpertCreation: what you get, prices, payment, start and refunds.",
                  "Your XpertCreation orders: active boosts and plans, payments, methods and receipts.")):
        page = page.replace(a, b)
    page = page.replace('<meta name="robots" content="index', '<meta name="robots" content="noindex')
    scr = re.findall(r"<script(?![^>]*\bsrc=)(?![^>]*ld\+json)[^>]*>(.*?)</script>", page, re.S)
    okjs = True
    for k, s in enumerate(scr):
        open("/tmp/xc_ord_%d.js" % k, "w").write(s)
        okjs = okjs and sh("node --check /tmp/xc_ord_%d.js" % k)[0] == 0
        os.remove("/tmp/xc_ord_%d.js" % k)
    print("  %-40s %s" % ("orders page script check", "ok" if okjs else "PROBLEM")); bad = bad or not okjs
if bad:
    print("\nSTOP - nothing changed. Send me the lines above."); bye(1)
if not APPLY:
    print("\nDry run OK - nothing changed. Run again with --apply."); bye(0)

print("== Installing")
bak = "/root/orders_bak_" + datetime.now().strftime("%Y%m%d_%H%M%S"); os.makedirs(bak)
for p in (SV, CBV, PR, NGINX, LAND + "/sw.js") + ((PBV,) if pb else ()):
    shutil.copy2(p, bak + "/" + os.path.basename(p) + ("." + p.split("/")[-2] if p.endswith("views.py") else ""))
print("  backup:", bak)


def rollback(why):
    for p in (SV, CBV) + ((PBV,) if pb else ()):
        shutil.copy2(bak + "/views.py." + p.split("/")[-2], p)
    sh("systemctl restart gunicorn-academy")
    print("FAILED (%s) - API files rolled back." % why); bye(1)


if "setup_orders_v1" not in sv:
    open(SV, "a", encoding="utf-8").write(SHOP_ADD)
if pb and "setup_orders_v1" not in pb:
    open(PBV, "w", encoding="utf-8").write(pb.replace(PB_A, PB_B, 1))
c2 = cb
for i, (a, b) in enumerate(CB):
    if b not in c2 and c2.count(a) == 1:
        c2 = c2.replace(a, b, 1)
open(CBV, "w", encoding="utf-8").write(c2)
c, out = sh("cd %s && %s manage.py check" % (API, py))
if c != 0:
    rollback("check: " + out[-300:])
sh("systemctl restart gunicorn-academy"); time.sleep(4)
open("/tmp/xc_fix.py", "w").write(FIX)
c, out = sh("cd %s && %s manage.py shell < /tmp/xc_fix.py" % (API, py)); os.remove("/tmp/xc_fix.py")
m = re.search(r"XCFIX (\d+)", out)
print("  OK   earnings register: JazzCash and Google Play now count as real income (%s old entries corrected), Google fee added" % (m.group(1) if m else "?"))
open(OUT, "w", encoding="utf-8").write(page)
if "/orders" not in pr:
    open(PR, "w", encoding="utf-8").write(pr.replace(PR_A, PR_B, 1))
if "location = /orders " not in ng:
    e = ng.index("\n", i_ng) + 1
    open(NGINX, "w").write(ng[:e] + "    location = /orders  { try_files /orders.html =404; }\n" + ng[e:])
    if sh("nginx -t")[0] != 0:
        shutil.copy2(bak + "/" + os.path.basename(NGINX), NGINX); print("  nginx test failed - nginx left as it was")
    else:
        sh("systemctl reload nginx")
cc = {p: code(p) for p in ("/orders", "/promote", "/api/shop/", "/receipt")}
print("  checks:", cc)
if any(v != "200" for v in cc.values()):
    rollback("site check")
print("  OK   /orders page, link on Promote, receipts show the real payment method")
s = open(LAND + "/sw.js").read(); m = re.search(r"xc-v(\d+)", s)
if m:
    open(LAND + "/sw.js", "w").write(s.replace(m.group(0), "xc-v%d" % (int(m.group(1)) + 1), 1)); print("  OK   sw.js", m.group(0), "->", "xc-v%d" % (int(m.group(1)) + 1))
WJ = "/root/scripts/whatsnew.json"
if os.path.exists(WJ):
    w = json.load(open(WJ, encoding="utf-8"))
    if not any(x.get("title") == ENTRY["title"] for x in w.get("items", [])):
        w["items"].insert(0, dict(ENTRY, date=datetime.now().strftime("%Y-%m-%d")))
    open(WJ, "w", encoding="utf-8").write(json.dumps(w, ensure_ascii=False, indent=1))
    if os.path.exists("/root/scripts/whatsnew_build.py"):
        sh("python3 /root/scripts/whatsnew_build.py")
    print("  OK   What's new entry")
print("\nDone. Members: xpertcreation.com/orders   |   Team (platform earnings): xpertcreation.com/company-register")
bye(0)
