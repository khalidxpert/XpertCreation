#!/usr/bin/env python3
# setup_shopsite_v1: no more getting stuck on the company / shop steps.
#  - Step 1 on the company page now offers two choices:
#      * "I have my own website" (the file check, as before), or
#      * "Use a free XpertCreation address": name.xpertcreation.com (or xpertcreation.com/s/name until the
#        Cloudflare * record is added). No website check: KYC alone verifies the company, then the shop can open.
#  - "Typed something wrong? Start over" deletes a company page that is not approved yet, so it can be typed again.
#  - A wrong website can be changed any time ("Use my own website instead" / "Change the address").
#  - A company or shop name fixed before approval also fixes its link (no typo stays in the URL).
#  - A shop waiting for approval gets "Fix my application" (it could not be edited before).
#  - xpertcreation.com/s/<name> and <name>.xpertcreation.com open that member's shop (or company page).
#   python3 /root/setup_shopsite_v1.py            dry run
#   python3 /root/setup_shopsite_v1.py --apply    install (backup in /root/shopsite_bak_<time>)
import glob, os, pwd, re, shutil, subprocess, sys, time
from datetime import datetime

API = os.environ.get("XC_API", "/var/www/xpertcreation-api")
LAND = os.environ.get("XC_LAND", "/var/www/xpertcreation-landing")
NGX_DIR = os.environ.get("XC_NGX", "/etc/nginx/sites-enabled")
NGINX, SUBS = NGX_DIR + "/xpertcreation-landing", NGX_DIR + "/xpertcreation-subs"
FLAG = os.environ.get("XC_FLAG", "/etc/xpertcreation/subdomains_on")
BAK = os.environ.get("XC_BAK", "/root/shopsite_bak_")
MARK = "(shopsite v1)"
FIXED = ["www", "api", "app", "apps", "m", "mail", "webmail", "smtp", "imap", "pop", "ftp", "ns1", "ns2", "admin", "cpanel", "root",
         "learn", "academy", "penflow", "wp", "irc", "chat", "blog", "shop", "store", "food", "wheels", "jobs", "help", "support",
         "status", "dev", "test", "staging", "static", "cdn", "media", "assets", "files", "docs", "team", "official", "xpert",
         "xpertcreation", "xpertconnect", "khalid", "khalidxpert", "login", "register", "account", "pay", "payments", "billing",
         "s", "go", "my", "new", "secure", "security", "verify", "google", "play", "digitalbloom", "digitalbloomco"]
C_CLK_A = '    if (a === "another"){ C = null; draw(); return; }\n'
C_CLK_B = '    if (a === "another"){ C = null; draw(); return; }\n    if (a === "pickown" || a === "picksub"){ C.site_pick = a === "picksub" ? "sub" : "own"; draw(); if (a === "picksub" && $("cmsubn")) $("cmsubn").focus(); return; }\n    if (a === "subsave"){ msg("cmm3", "Saving…"); api(C.id + "/site/", {method: "POST", body: {mode: "sub", name: v("cmsubn")}}).then(function(r){ upd(r, "cmm3", "✔ Address saved. Now step 2: KYC."); }); return; }\n    if (a === "restart"){ if (!confirm("Start over?\\n\\nThis deletes this company page: its name, link, website and documents. Then you can type it again.")) return;\n      api(C.id + "/restart/", {method: "POST", body: {}}).then(function(r){ if (!r.ok){ msg("cmm1", (r.data && r.data.detail) || "Could not start over.", "bad"); return; } var id = C.id; list = list.filter(function(x){ return x.id !== id; }); C = null; draw(); msg("cmm0", "Deleted. Type the company name again.", "ok"); }); return; }\n'
C_CSS_A = '.cmimgs{display:flex;gap:12px;'
C_CSS_B = '.cmpick2{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:6px}@media(max-width:560px){.cmpick2{grid-template-columns:1fr}}.cmopt{display:flex;flex-direction:column;gap:4px;text-align:left;padding:14px;border-radius:14px;border:1.5px solid var(--line,#E4E8F2);background:#fff;cursor:pointer;font:inherit;color:inherit}.cmopt:hover{border-color:#1B4DFF}.cmopt b{font-size:15px}.cmopt small{font-size:13px;color:#5A657C;line-height:1.4}.cmlink{background:none;border:0;padding:6px 0;color:#1B4DFF;font:inherit;font-size:14px;font-weight:700;cursor:pointer;text-decoration:underline}.cmsub{display:flex;align-items:center;border:1px solid var(--line,#E4E8F2);border-radius:12px;overflow:hidden;background:#fff}.cmsub input{border:0!important;margin:0!important;flex:1;min-width:0;border-radius:0!important}.cmsub span{padding:0 12px;color:#5A657C;font-weight:700;white-space:nowrap;font-size:14px}.cmsub span.pre{padding-right:0}\n.cmimgs{display:flex;gap:12px;'
C_NEW_A = 'Free. Step 1 verifies your website, step 2 verifies your company (KYC) for the \\u2714 Verified badge.'
C_NEW_B = 'Free. Step 1: your own website, or a free XpertCreation address. Step 2: KYC for the \\u2714 Verified badge.'
C_S1_END = '      + \'<div class="cmmsg" id="cmm3"></div></div>\';\n'
C_S1_NEW = '    var sub = C.site_mode === "sub" && C.subdomain, s1 = C.website_verified || !!sub, pick = C.site_pick || "";\n    var own = C.site_mode === "own" || (!C.site_mode && !!(C.domain_pending || C.website));\n    var ownForm = \'<p class="sub">Prove the company runs its website. Your page goes public after this.</p>\' + f("cmdom", "Company website", C.domain_pending || (C.website || "").replace(/^https?:\\/\\//, ""), "text", "mycompany.com")\n      + \'<button class="cmbtn g" data-a="dom">Get my file</button>\'\n      + (C.domain_token ? \'<ol style="font-size:14px;line-height:1.7;padding-left:20px"><li><button class="cmbtn g" style="margin:0" data-a="domdl">⬇ Download xpertcreation-verify.txt</button></li>\'\n        + \'<li>Upload it to the main folder of your website, so it opens at <b>https://\' + esc(C.domain_pending) + \'/xpertcreation-verify.txt</b></li><li>Then tap <b>Check now</b>.</li></ol><button class="cmbtn" data-a="domchk">Check now</button>\' : \'\')\n      + \'<p><button class="cmlink" data-a="picksub">No website? Use a free XpertCreation address instead</button></p>\';\n    var sugg = C.subdomain || String(C.name || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 30);\n    var subForm = \'<p class="sub">No website needed. Pick your address: English letters, numbers and - only. Our team verifies you with KYC in step 2.</p>\'\n      + \'<label for="cmsubn">Your free address</label><div class="cmsub">\' + (C.sub_live ? \'\' : \'<span class="pre">xpertcreation.com/s/</span>\') + \'<input id="cmsubn" maxlength="30" autocapitalize="off" autocomplete="off" spellcheck="false" value="\' + esc(sugg) + \'" placeholder="bilal-traders">\' + (C.sub_live ? \'<span>.xpertcreation.com</span>\' : \'\') + \'</div>\'\n      + \'<button class="cmbtn" data-a="subsave">Use this address</button><p><button class="cmlink" data-a="pickown">I have my own website</button></p>\';\n    h += \'<div class="cmb"><h2><span class="n\' + (s1 ? " ok" : "") + \'">\' + (s1 ? "✔" : "1") + \'</span> Your web address</h2>\';\n    if (C.website_verified && pick !== "sub") h += \'<p class="sub">🌐 \' + esc(C.domain) + \' is verified. Your page is public.</p>\';\n    else if (pick === "sub") h += subForm;\n    else if (pick === "own") h += ownForm;\n    else if (sub) h += \'<p class="sub">✨ Your free address: <b>\' + esc(String(C.sub_url || "").replace(/^https?:\\/\\//, "")) + \'</b><br>No website check needed: our team verifies you with KYC in step 2. It opens your shop once the shop is approved.</p><button class="cmbtn g" data-a="picksub">Change the address</button> <button class="cmlink" data-a="pickown">Use my own website instead</button>\';\n    else if (own) h += ownForm;\n    else h += \'<p class="sub">Pick one. You can change it later.</p><div class="cmpick2"><button class="cmopt" data-a="pickown"><b>🌐 I have my own website</b><small>Like mycompany.com. We check it with a small file you upload.</small></button>\'\n      + \'<button class="cmopt" data-a="picksub"><b>✨ Use a free XpertCreation address</b><small>Like yourname.xpertcreation.com. No website needed: KYC verifies you.</small></button></div>\';\n    h += \'<div class="cmmsg" id="cmm3"></div></div>\';\n'
C_S1_START = '    var s1 = C.website_verified;\n'
C_ST_A = '    h += \'<div class="cmst \' + C.status + \'">\' + esc(st) + \'</div>\';\n'
C_ST_B = '    h += \'<div class="cmst \' + C.status + \'">\' + esc(st) + \'</div>\';\n    if (C.status !== "approved") h += \'<p style="text-align:right;margin:-4px 0 8px"><button class="cmlink" data-a="restart">\\u21BA Typed something wrong? Start over</button></p>\';\n'
H_BTN_A = '\'<p><button class="st-btn o" id="ago">Apply for a shop</button></p>'
H_BTN_B = '\'<p><button class="st-btn o" id="ago">\' + (m && m.status === "pending" ? "Save my application" : "Apply for a shop") + \'</button></p>'
H_OK_A = '|| (m && m.status === "rejected");'
H_OK_B = '|| (m && (m.status === "rejected" || m.status === "pending"));'
H_PEND_A = "You will get a notification.</div>'; return; }"
H_PEND_B = 'You will get a notification.<br><button class="st-btn sm" id="apEdit" style="margin-top:12px">&#9998; Typed something wrong? Fix my application</button></div>\'; $("apEdit").onclick = function(){ applyForm(m); }; return; }'
MODEL_ADD = '    site_mode = models.CharField(max_length=4, blank=True, default="")   # "" not chosen | own (own website) | sub (free XpertCreation address)\n    subdomain = models.CharField(max_length=30, blank=True, default="", db_index=True)\n'
MODEL_ANCH = '    domain_verified_at = models.DateTimeField(null=True, blank=True)\n'
S_BIZ_A = '    out["ok"] = out["approved"] and out["website"]'
S_BIZ_B = '    out["sub"] = getattr(c, "site_mode", "") == "sub" and bool(getattr(c, "subdomain", ""))\n    out["ok"] = out["approved"] and (out["website"] or out["sub"])     # own website checked, or a free XpertCreation address (KYC only)'
S_LBL_A = '"a verified business: company page approved by our team and its website checked with the verification file"'
S_LBL_B = '"a verified business: company page approved by our team (your own website checked, or a free xpertcreation.com address)"'
S_SLUG_A = '        m.name, m.city, m.phone, m.kind = name, city, phone, kind\n'
S_SLUG_B = '        if not new and m.status in ("pending", "rejected") and name != m.name:   # fix a typo: the link follows the new name\n            base = slugify(name)[:70] or "shop"\n            slug, n = base, 2\n            while Merchant.objects.filter(slug=slug).exclude(pk=m.pk).exists():\n                slug = "%s-%d" % (base, n); n += 1\n            m.slug = slug\n        m.name, m.city, m.phone, m.kind = name, city, phone, kind\n'
U_A = '    path("<int:pk>/domain/", views.domain, name="co-domain"),\n'
U_B = '    path("<int:pk>/domain/", views.domain, name="co-domain"),\n    path("<int:pk>/site/", views.site, name="co-site"),\n    path("<int:pk>/restart/", views.restart, name="co-restart"),\n    path("go/<str:name>/", views.go, name="co-go"),\n'
V_DOM_A = '    return Response(_out(c, True))\n\n\nMAGIC = '
V_DOM_B = '    if c.site_mode != "own" or c.subdomain:\n        c.site_mode, c.subdomain = "own", ""\n        c.save(update_fields=["site_mode", "subdomain", "updated_at"])\n    return Response(_out(c, True))\n\n\nMAGIC = '
V_NAME_A = '            nm = _t(d.get("name"), 120)\n            if len(nm) >= 2: c.name = nm'
V_NAME_B = '            nm = _t(d.get("name"), 120)\n            if len(nm) >= 2 and nm != c.name:\n                c.name = nm\n                c.slug = _unique_slug(nm, c.pk)      # a typo in the name doesn\'t stay in the link (only before approval)'
V_NEW = '\n\n\n# ---------------------------------------------------------------- web address: own website, or a free name.xpertcreation.com (shopsite v1)\nSUBNAME = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,28}[a-z0-9])$")\nSUB_RESERVED = set(__RESERVED__)\nWILDCARD_FILE = "/etc/xpertcreation/subdomains_on"   \n\n\ndef sub_live():\n    """True once *.xpertcreation.com has a DNS record (Cloudflare) and the nginx block is on."""\n    return os.path.exists(WILDCARD_FILE)\n\n\ndef sub_url(c):\n    if c.site_mode != "sub" or not c.subdomain:\n        return ""\n    return ("https://%s.xpertcreation.com" % c.subdomain) if sub_live() else (SITE + "/s/" + c.subdomain)\n\n\ndef _sub_taken(name, c):\n    if name in SUB_RESERVED or "--" in name:\n        return "That address is reserved. Try another one."\n    if Company.objects.filter(subdomain=name).exclude(pk=c.pk).exists():\n        return "Someone already uses %s. Try another one." % name\n    try:\n        from store.models import Merchant\n        if Merchant.objects.filter(slug=name).exclude(user=c.owner).exists():\n            return "A shop already uses %s. Try another one." % name\n    except Exception:\n        pass\n    return ""\n\n\n@api_view(["POST"])\n@permission_classes([IsAuthenticated])\ndef site(request, pk):\n    """{mode: "sub", name: "bilal-traders"} takes a free address; {mode: "own"} goes back to your own website."""\n    c = Company.objects.filter(pk=pk, owner=request.user).first()\n    if not c:\n        return _err("Company not found.", 404)\n    mode = request.data.get("mode")\n    if mode == "own":\n        c.site_mode, c.subdomain = "own", ""\n        c.save(update_fields=["site_mode", "subdomain", "updated_at"])\n        return Response(_out(c, True))\n    if mode != "sub":\n        return _err("Pick your own website or a free XpertCreation address.")\n    name = re.sub(r"[^a-z0-9-]", "", re.sub(r"[\\s_.]+", "-", str(request.data.get("name") or "").strip().lower()))[:30].strip("-")\n    if not SUBNAME.match(name):\n        return _err("Use 3 to 30 English letters, numbers or - (like bilal-traders).")\n    e = _sub_taken(name, c)\n    if e:\n        return _err(e)\n    c.site_mode, c.subdomain = "sub", name\n    c.save(update_fields=["site_mode", "subdomain", "updated_at"])\n    return Response(_out(c, True))\n\n\n@api_view(["POST"])\n@permission_classes([IsAuthenticated])\ndef restart(request, pk):\n    """Start over: delete a company page that is not approved yet (name, link, website, documents)."""\n    c = Company.objects.filter(pk=pk, owner=request.user).first()\n    if not c:\n        return _err("Company not found.", 404)\n    if c.status == Company.APPROVED:\n        return _err("This company is verified. To change it, contact support.")\n    _wipe_docs(c); c.delete()\n    return Response({"deleted": True})\n\n\ndef go(request, name):\n    """xpertcreation.com/s/<name> and <name>.xpertcreation.com: open the member\'s shop, else the company page."""\n    from django.http import HttpResponseRedirect\n    name = str(name or "").lower()[:30]\n    c = Company.objects.filter(subdomain=name, site_mode="sub", hidden=False).select_related("owner").first()\n    try:\n        from store.models import Merchant\n        m = Merchant.objects.filter(user=c.owner, status="approved").first() if c else Merchant.objects.filter(slug=name, status="approved").first()\n    except Exception:\n        m = None\n    if m:\n        return HttpResponseRedirect(SITE + "/shop/" + m.slug)\n    if c and public_ok(c):\n        return HttpResponseRedirect(SITE + "/company/" + c.slug)\n    return HttpResponseRedirect(SITE + "/store#shops")\n'
V_OUT_A = '"domain_pending": c.domain, "domain_token": c.domain_token, "public": public_ok(c),'
V_OUT_B = '"domain_pending": c.domain, "domain_token": c.domain_token, "public": public_ok(c), "site_mode": c.site_mode, "subdomain": c.subdomain, "sub_url": sub_url(c), "sub_live": sub_live(),'
V_SLUG_A = 'def _unique_slug(name):\n    base = slugify(name)[:50] or "company"\n    s, i = base, 2\n    while Company.objects.filter(slug=s).exists() or s in ("new", "manage", "review"):'
V_SLUG_B = 'def _unique_slug(name, me=None):\n    base = slugify(name)[:50] or "company"\n    s, i = base, 2\n    while Company.objects.filter(slug=s).exclude(pk=me).exists() or s in ("new", "manage", "review"):'
V_SUB_A = '    if not c.domain_verified_at:\n        return _err("First verify your website (step 1).")'
V_SUB_B = '    if not (c.domain_verified_at or (c.site_mode == "sub" and c.subdomain)):\n        return _err("First finish step 1: verify your own website, or pick a free XpertCreation address.")'

fail = []


def need(label, ok, note=""):
    print("  %-52s %s" % (label, ("ok" if ok else "PROBLEM") + (" " + note if note else "")))
    if not ok:
        fail.append(label)


def bye(c):
    try:
        os.chdir("/root")
    except Exception:
        pass
    sys.exit(c)


def sh(c, t=300):
    r = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=t)
    return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()


def rd(p):
    try:
        return open(p, encoding="utf-8").read()
    except Exception:
        return ""


def code(p, host="xpertcreation.com"):
    return sh("curl -sk -o /dev/null -w '%%{http_code} %%{redirect_url}' -H 'Host: %s' 'https://127.0.0.1%s'" % (host, p))[1]


APPLY = "--apply" in sys.argv
py = next((p for p in (API + "/venv/bin/python", API + "/.venv/bin/python") if os.path.exists(p)), "python3")
F = {"model": API + "/companies/models.py", "views": API + "/companies/views.py", "urls": API + "/companies/urls.py",
     "store": API + "/store/views.py", "chtml": LAND + "/companies.html", "shtml": LAND + "/store.html"}
S = {k: rd(v) for k, v in F.items()}
UP = MARK in S["views"]
print("== Checks  (mode: %s)" % ("already installed - only the subdomain switch is checked" if UP else "fresh install"))

# names nobody may take: every *.xpertcreation.com that nginx already serves + a fixed list
taken = set()
for f in glob.glob(NGX_DIR + "/*"):
    for m in re.finditer(r"server_name\s+([^;]+);", rd(f)):
        for h in m.group(1).split():
            if h.endswith(".xpertcreation.com") and not h.startswith("~"):
                taken.add(h[:-len(".xpertcreation.com")].split(".")[-1])
RES = sorted(set(FIXED) | taken)

PATCH = [("model", MODEL_ANCH, MODEL_ANCH + MODEL_ADD), ("views", V_OUT_A, V_OUT_B), ("views", V_SLUG_A, V_SLUG_B), ("views", V_NAME_A, V_NAME_B),
         ("views", V_SUB_A, V_SUB_B), ("views", V_DOM_A, V_DOM_B), ("urls", U_A, U_B),
         ("store", S_BIZ_A, S_BIZ_B), ("store", S_LBL_A, S_LBL_B), ("store", S_SLUG_A, S_SLUG_B),
         ("shtml", H_PEND_A, H_PEND_B), ("shtml", H_OK_A, H_OK_B), ("shtml", H_BTN_A, H_BTN_B),
         ("chtml", C_CSS_A, C_CSS_B), ("chtml", C_NEW_A, C_NEW_B), ("chtml", C_ST_A, C_ST_B), ("chtml", C_CLK_A, C_CLK_B)]
NEW = dict(S)
if not UP:
    for k, a, b in PATCH:
        n = NEW[k].count(a)
        need("%s: %s" % (os.path.basename(F[k]), a.strip().split("\n")[0][:44]), n == 1, "" if n == 1 else "found %d times" % n)
        if n == 1:
            NEW[k] = NEW[k].replace(a, b, 1)
    i0 = NEW["chtml"].find(C_S1_START); i1 = NEW["chtml"].find(C_S1_END, i0)
    need("companies.html: step 1 block", NEW["chtml"].count(C_S1_START) == 1 and i1 > i0)
    if i1 > i0:
        NEW["chtml"] = NEW["chtml"][:i0] + C_S1_NEW + NEW["chtml"][i1 + len(C_S1_END):]
    NEW["views"] = NEW["views"].rstrip("\n") + "\n" + V_NEW.replace("__RESERVED__", repr(RES)) + "\n"
    need("companies: _wipe_docs + public_ok exist", "def _wipe_docs(" in S["views"] and "def public_ok(" in S["views"])
    for k in ("chtml", "shtml"):
        s = re.findall(r"<script>(.*?)</script>", NEW[k], re.S)
        open("/tmp/xc_ss_%s.js" % k, "w", encoding="utf-8").write("\n;\n".join(s))
        rc, out = sh("node --check /tmp/xc_ss_%s.js" % k)
        need("%s scripts (node --check)" % os.path.basename(F[k]), rc == 0 or "not found" in out, out[:300] if rc else "")
    open("/tmp/xc_ss_v.py", "w").write(NEW["views"]); open("/tmp/xc_ss_s.py", "w").write(NEW["store"])
    need("python syntax", sh("%s -m py_compile /tmp/xc_ss_v.py /tmp/xc_ss_s.py" % py)[0] == 0)
ng = rd(NGINX)
i_ng = ng.find("    location = /tools ")
need("nginx anchor (location = /tools)", "location ^~ /s/" in ng or i_ng != -1, "already done" if "location ^~ /s/" in ng else "")
need("nothing else uses /s/ on the site", "location ^~ /s/" in ng or (not re.search(r"location\s+[^{]*\s/s/", ng) and not os.path.exists(LAND + "/s")))
cert = re.search(r"ssl_certificate\s+([^;]+);", ng); ckey = re.search(r"ssl_certificate_key\s+([^;]+);", ng)
need("site certificate found in nginx", bool(cert and ckey))
six = bool(re.search(r"listen\s+\[::\]:443", "".join(rd(f) for f in glob.glob(NGX_DIR + "/*"))))
probe = "xcprobe%d" % int(time.time())
dns = sh("getent hosts %s.xpertcreation.com" % probe)[0] == 0
print("  names reserved (already used on the server): %s" % ", ".join(sorted(taken)) or "-")
print("  *.xpertcreation.com in DNS:", "yes" if dns else "not yet (free addresses work as xpertcreation.com/s/name until then)")
if fail:
    print("\nStopped: send me these lines."); bye(1)
if not APPLY:
    print("\nDry run OK - nothing changed. Run again with --apply."); bye(0)

print("== Installing")
bak = BAK + datetime.now().strftime("%Y%m%d_%H%M%S"); os.makedirs(bak)
for k, p in list(F.items()) + [("ngx", NGINX), ("sw", LAND + "/sw.js")]:
    if os.path.exists(p):
        shutil.copy2(p, bak + "/" + k + "_" + os.path.basename(p))
print("  backup:", bak)
user = pwd.getpwuid(os.stat(API + "/manage.py").st_uid).pw_name
migs = set(glob.glob(API + "/companies/migrations/0*.py"))


def putback(why):
    for k, p in F.items():
        shutil.copy2(bak + "/" + k + "_" + os.path.basename(p), p)
    for m in set(glob.glob(API + "/companies/migrations/0*.py")) - migs:
        os.remove(m)
    sh("systemctl restart gunicorn-academy")
    print("\nFAILED (%s) - code put back. Send me the lines above." % why); bye(1)


def run(*a):
    r = subprocess.run([py, "manage.py"] + list(a), cwd=API, capture_output=True, text=True)
    if r.returncode:
        print((r.stdout or "")[-1500:], (r.stderr or "")[-1500:])
    return r.returncode == 0


if not UP:
    for k in ("model", "views", "urls", "store"):
        open(F[k], "w", encoding="utf-8").write(NEW[k])
    if not (run("makemigrations", "companies") and run("migrate", "companies") and run("check")):
        putback("migrate")
    sh("chown -R %s: %s/companies %s/store" % (user, API, API))
    sh("systemctl restart gunicorn-academy"); time.sleep(5)
    cc = {}
    for _ in range(5):
        cc = {"go": code("/api/companies/go/xcnothing/"), "mine": code("/api/companies/mine/"), "site": sh("curl -sk -o /dev/null -w '%{http_code}' -X POST -H 'Host: xpertcreation.com' https://127.0.0.1/api/companies/1/site/")[1]}
        if cc["go"].startswith("302"):
            break
        time.sleep(3)
    print("  API check:", cc)
    if not (cc["go"].startswith("302") and cc["mine"][:3] in ("401", "403") and cc["site"][:3] in ("401", "403")):
        putback("API check")
    own = sh("stat -c %U:%G " + F["chtml"])[1]
    for k in ("chtml", "shtml"):
        open(F[k], "w", encoding="utf-8").write(NEW[k])
        sh("chown %s %s" % (own, F[k]))
    w = rd(LAND + "/sw.js"); m = re.search(r"xc-v(\d+)", w)
    if m:
        open(LAND + "/sw.js", "w", encoding="utf-8").write(w.replace(m.group(0), "xc-v%d" % (int(m.group(1)) + 1), 1))
    print("  OK   web address choice, Start over, name fixes")

# nginx: /s/<name> for everyone now, and <name>.xpertcreation.com once the DNS record is there
ch = False
if "location ^~ /s/" not in ng:
    e = ng.index("\n", i_ng) + 1
    open(NGINX, "w").write(ng[:e] + '    location ^~ /s/ { rewrite "^/s/([A-Za-z0-9-]{1,30})/?$" /api/companies/go/$1/ last; return 404; }\n' + ng[e:]); ch = True
skip = "|".join(re.escape(x) for x in ["www"] + sorted(taken))
blk = ("# setup_shopsite_v1: <name>.xpertcreation.com opens that member's shop. Real subdomains (learn, wp, ...) have their own blocks and win.\n"
       "server {\n    listen 80;%s\n    server_name \"~^(?!(%s)\\.)(?<xcsub>[a-z0-9-]{1,30})\\.xpertcreation\\.com$\";\n    return 302 https://xpertcreation.com/s/$xcsub;\n}\n"
       "server {\n    listen 443 ssl;%s\n    server_name \"~^(?!(%s)\\.)(?<xcsub>[a-z0-9-]{1,30})\\.xpertcreation\\.com$\";\n    ssl_certificate %s;\n    ssl_certificate_key %s;\n    return 302 https://xpertcreation.com/s/$xcsub;\n}\n") % (
    "\n    listen [::]:80;" if six else "", skip, "\n    listen [::]:443 ssl;" if six else "", skip, cert.group(1).strip(), ckey.group(1).strip())
if rd(SUBS) != blk:
    open(SUBS, "w").write(blk); ch = True
if ch:
    rc, out = sh("nginx -t")
    if rc != 0:
        print(out[-600:])
        shutil.copy2(bak + "/ngx_" + os.path.basename(NGINX), NGINX)
        if os.path.exists(SUBS):
            os.remove(SUBS)
        print("  nginx test failed - nginx put back (the rest is installed)")
    else:
        sh("systemctl reload nginx"); time.sleep(2)
print("  /s/xcnothing        ->", code("/s/xcnothing"))
print("  test.xpertcreation  ->", code("/", "xcnothing.xpertcreation.com"))
print("  learn.xpertcreation ->", code("/", "learn.xpertcreation.com"), "(must NOT go to /s/)")
os.makedirs(os.path.dirname(FLAG), exist_ok=True)
if dns and os.path.exists(SUBS):
    open(FLAG, "w").write("on\n"); os.chmod(FLAG, 0o644)
    print("  OK   free addresses show as name.xpertcreation.com")
else:
    if os.path.exists(FLAG):
        os.remove(FLAG)
    print("  free addresses show as xpertcreation.com/s/name for now. To switch on name.xpertcreation.com:")
    print("       Cloudflare -> xpertcreation.com -> DNS -> Add record: Type A, Name *, IPv4 = this server's IP, Proxy ON (orange)")
    print("       then run this installer again with --apply (it only flips the switch).")
print("\nDone. Shahzaib: open xpertcreation.com/company/manage, tap 'Typed something wrong? Start over' or")
print("'No website? Use a free XpertCreation address', then send KYC (step 2).")
bye(0)
