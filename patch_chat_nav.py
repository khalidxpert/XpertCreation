#!/usr/bin/env python3
# Notifications on/off moves to the Account (gear) page; a chat icon with an unread badge in the
# home header; the recent-chats box leaves the home page; "+ New chat" on the chat page lists your connections.
#   python3 /root/patch_chat_nav.py            dry run
#   python3 /root/patch_chat_nav.py --apply    write (backups in /root)
import os, re, sys, shutil, subprocess
from datetime import datetime
LAND = os.environ.get("LAND", "/var/www/xpertcreation-landing")
APPLY = "--apply" in sys.argv
PUSH_JS = '/* Notifications on this phone or computer: the "Turn on" bar, and subscribe / unsubscribe.\n   Shows in any element with id="pushbar". */\n(function(){\n  "use strict";\n  var bar = document.getElementById("pushbar");\n  if (!bar) return;\n  var ok = "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;\n  function cookie(n){ var m = document.cookie.match("(^|;)\\\\s*" + n + "\\\\s*=\\\\s*([^;]+)"); return m ? m.pop() : ""; }\n  function post(p, body){\n    return fetch("/api/notify/push/" + p, {method: "POST", credentials: "same-origin",\n      headers: {"Content-Type": "application/json", "X-CSRFToken": cookie("xc_csrf")}, body: JSON.stringify(body || {})});\n  }\n  function b64(s){\n    var pad = "=".repeat((4 - s.length % 4) % 4), raw = atob((s + pad).replace(/-/g, "+").replace(/_/g, "/"));\n    var out = new Uint8Array(raw.length);\n    for (var i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);\n    return out;\n  }\n  function reg(){ return navigator.serviceWorker.register("/sw.js").then(function(){ return navigator.serviceWorker.ready; }); }\n  function box(html){\n    bar.innerHTML = html ? "<div style=\'display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:10px 0;padding:11px 14px;"\n      + "border:1px solid var(--line,#E4E8F2);border-radius:14px;background:var(--card,#fff);font-size:14px\'>" + html + "</div>" : "";\n  }\n  var BTN = "padding:7px 13px;border-radius:10px;font-weight:700;cursor:pointer;border:1px solid var(--line,#E4E8F2);";\n  function draw(){\n    if (!ok){ box(""); return; }\n    if (Notification.permission === "denied"){ box("\\uD83D\\uDD15 Notifications are blocked for this site. Allow them in your browser\'s site settings to hear about new messages."); return; }\n    reg().then(function(r){ return r.pushManager.getSubscription(); }).then(function(sub){\n      if (sub && Notification.permission === "granted"){\n        box(bar.getAttribute("data-quiet") ? "" : "\\uD83D\\uDD14 Notifications are on for this device. <span style=\'flex:1\'></span>"\n          + "<button data-push=\'test\' style=\'" + BTN + "background:var(--card,#fff)\'>Send a test</button>"\n          + "<button data-push=\'off\' style=\'" + BTN + "background:var(--card,#fff)\'>Turn off</button>");\n      } else {\n        box("\\uD83D\\uDD14 Notifications on this device: new messages, connection requests and reminders, even when the site is closed. <span style=\'flex:1\'></span>"\n          + "<button data-push=\'on\' style=\'" + BTN + "background:var(--brand,#1B4DFF);color:#fff;border-color:var(--brand,#1B4DFF)\'>Turn on</button>");\n      }\n    }).catch(function(){ box(""); });\n  }\n  bar.addEventListener("click", function(e){\n    var b = e.target.closest("[data-push]");\n    if (!b) return;\n    var what = b.getAttribute("data-push");\n    b.disabled = true;\n    if (what === "on"){\n      Notification.requestPermission().then(function(p){\n        if (p !== "granted") return draw();\n        return fetch("/api/notify/push/key/").then(function(r){ return r.json(); }).then(function(k){\n          if (!k.key) throw new Error("no key");\n          return reg().then(function(r){ return r.pushManager.subscribe({userVisibleOnly: true, applicationServerKey: b64(k.key)}); });\n        }).then(function(sub){ return post("subscribe/", sub.toJSON()); }).then(draw);\n      }).catch(function(){ b.disabled = false; alert("Could not turn on notifications on this device."); });\n    } else if (what === "off"){\n      reg().then(function(r){ return r.pushManager.getSubscription(); }).then(function(sub){\n        if (!sub) return;\n        return post("unsubscribe/", {endpoint: sub.endpoint}).then(function(){ return sub.unsubscribe(); });\n      }).then(draw);\n    } else if (what === "test"){\n      post("test/").then(function(){ b.textContent = "Sent \\u2713"; });\n    }\n  });\n  fetch("/api/auth/me/", {credentials: "same-origin"}).then(function(r){ if (r.ok) draw(); }).catch(function(){});\n})();\n'
NEWCHAT = '    if (e.target.closest("#newchat3")){\n      var nl = $("newlist3");\n      if (nl.innerHTML){ nl.innerHTML = ""; return; }\n      nl.innerHTML = \'<div class="empty8">Loading your connections\\u2026</div>\';\n      fetch("/api/network/me/people/connections/", {credentials: "same-origin"}).then(function(r){ return r.json(); }).then(function(d){\n        var list = (d && d.people) || [];\n        if (!list.length){\n          nl.innerHTML = \'<div class="empty8">You can chat with people you are connected to. Find people in \'\n            + \'<a href="/people">Connect</a> and send a request; once they accept, they appear here.</div>\';\n          return;\n        }\n        nl.innerHTML = \'<input id="ncq3" placeholder="Search your connections" style="width:100%;padding:11px 13px;border:1.5px solid var(--line);border-radius:12px;margin-bottom:8px;font:inherit">\'\n          + \'<div id="ncl3">\' + list.map(function(p){\n              return \'<div class="trow2" data-newc="\' + esc(p.slug || "") + \'" data-name="\' + esc(p.name.toLowerCase()) + \'">\'\n                + \'<span class="av6">\' + esc(p.name.charAt(0).toUpperCase()) + \'</span>\'\n                + \'<span class="t3"><b>\' + esc(p.name) + \'</b><small>\' + esc(p.headline || "") + \'</small></span></div>\';\n            }).join("") + \'</div>\';\n      }).catch(function(){ nl.innerHTML = \'<div class="empty8">Could not load your connections.</div>\'; });\n      return;\n    }\n    var nc = e.target.closest("[data-newc]");\n    if (nc){\n      var slug = nc.getAttribute("data-newc");\n      if (!slug) return;\n      nc.style.opacity = ".5";\n      fetch("/api/network/in/" + encodeURIComponent(slug) + "/message/", {method: "POST", credentials: "same-origin",\n            headers: {"Content-Type": "application/json", "X-CSRFToken": cookie("xc_csrf")}, body: "{}"})\n        .then(function(r){ return r.json().then(function(d){ return {ok: r.ok, d: d}; }); })\n        .then(function(x){\n          nc.style.opacity = "";\n          if (!x.ok){ alert(x.d.detail || "Could not open the chat."); return; }\n          $("newlist3").innerHTML = "";\n          loadList().then(function(){ openThread(x.d.id); });\n        });\n      return;\n    }\n'
HOME_ICON = '    <a class="gear" id="chatBtn" href="/chat" aria-label="Chat" title="Chat" style="position:relative"><svg viewBox="0 0 24 24"><path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/></svg><span id="chatBadgeHome" style="display:none;position:absolute;top:-4px;right:-4px;min-width:17px;height:17px;padding:0 4px;border-radius:99px;background:#DC2626;color:#fff;font-size:10.5px;font-weight:800;line-height:17px;text-align:center"></span></a>\n'
HOME_BADGE = '<script>\n/* Unread chat messages on the chat icon in the home header. */\n(function(){\n  function go(){\n    if (document.hidden) return;\n    fetch("/api/notify/threads/unread/", {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; }).then(function(d){\n      var b = document.getElementById("chatBadgeHome"), n = d && d.unread ? d.unread : 0;\n      if (!b) return;\n      b.style.display = n ? "" : "none";\n      b.textContent = n > 99 ? "99+" : String(n);\n    }).catch(function(){});\n  }\n  setTimeout(go, 900);\n  setInterval(go, 60000);\n})();\n</script>\n'
CSS = (".newc3{margin-top:12px}.newc3 button{padding:10px 16px;border-radius:12px;background:var(--brand);color:#fff;font-weight:800;border:0;cursor:pointer}"
       "#newlist3{margin-top:10px}body.inchat .newc3,body.inchat #newlist3{display:none}\n")
PUSHBAR = re.compile(r'<script src="/js/push-1\.js" defer></script>\n<div id="pushbar"( data-quiet="1")?></div>\n')
RECENT = re.compile(r'<div id="recentchats"></div>\n<script>\n/\* Recent chats on the home page.*?</script>\n', re.S)

fail = []
def need(label, ok):
    print("  %-40s %s" % (label, "ok" if ok else "PROBLEM"))
    if not ok: fail.append(label)
files = {n: LAND + "/" + n for n in ("chat.html", "index.html", "account.html")}
s = {n: open(p, encoding="utf-8").read() for n, p in files.items()}
c = s["chat.html"]
need("chat: notifications bar", len(PUSHBAR.findall(c)) == 1)
need("chat: list spot", c.count('  <div id="list5" style="margin-top:14px"></div>') == 1)
need("chat: click spot", c.count('    if (e.target.id === "csend") send();') == 1)
need("chat: css spot", c.count(".empty8{") == 1)
need("chat: not done yet", "newchat3" not in c)
c = PUSHBAR.sub("", c, 1)
c = c.replace('  <div id="list5" style="margin-top:14px"></div>',
              '  <div class="newc3"><button id="newchat3" type="button">+ New chat</button></div>\n  <div id="newlist3"></div>\n'
              '  <div id="list5" style="margin-top:14px"></div>', 1)
c = c.replace('    if (e.target.id === "csend") send();', NEWCHAT + '    if (e.target.id === "csend") send();', 1)
c = c.replace(".empty8{", CSS + ".empty8{", 1)
ix = s["index.html"]
need("home: notifications bar", len(PUSHBAR.findall(ix)) == 1)
need("home: recent chats box", len(RECENT.findall(ix)) == 1)
need("home: settings icon", ix.count('    <a class="gear" id="gearBtn" href="/account"') == 1)
need("home: no chat icon yet", 'id="chatBtn"' not in ix)
ix = RECENT.sub("", PUSHBAR.sub("", ix, 1), 1)
ix = ix.replace('    <a class="gear" id="gearBtn" href="/account"', HOME_ICON + '    <a class="gear" id="gearBtn" href="/account"', 1)
i = ix.rfind("</body>")
need("home: </body>", i > 0)
ix = ix[:i] + HOME_BADGE + ix[i:]
ac = s["account.html"]
need("account: main card", ac.count('<div class="card" id="card"></div></main>') == 1)
need("account: no notifications bar yet", "pushbar" not in ac)
ac = ac.replace('<div class="card" id="card"></div></main>', '<div class="card" id="card"></div><div id="pushbar"></div></main>', 1)
j = ac.rfind("</body>")
ac = ac[:j] + '<script src="/js/push-1.js?v=2" defer></script>\n' + ac[j:]
new = {"chat.html": c, "index.html": ix, "account.html": ac}
for n, html in new.items():
    bad = []
    for k, b in enumerate(re.findall(r"<script>(.*?)</script>", html, re.S)):
        open("/tmp/cn.js", "w", encoding="utf-8").write(b)
        r = subprocess.run(["node", "--check", "/tmp/cn.js"], capture_output=True, text=True)
        if r.returncode: bad.append(r.stderr[:300])
    need("node --check " + n, not bad)
    for b in bad: print(b)
open("/tmp/cn.js", "w").write(PUSH_JS)
need("node --check push-1.js", subprocess.run(["node", "--check", "/tmp/cn.js"], capture_output=True).returncode == 0)
if fail:
    sys.exit("\nSTOP - " + ", ".join(fail) + ". Nothing written.")
if not APPLY:
    print("\nDRY RUN OK - nothing written. Run again with --apply."); sys.exit(0)
bak = "/root/chatnav_bak_" + datetime.now().strftime("%Y%m%d_%H%M%S")
os.makedirs(bak)
for n, p in files.items():
    shutil.copy(p, bak + "/" + n)
shutil.copy(LAND + "/js/push-1.js", bak + "/push-1.js")
for n, html in new.items():
    open(files[n], "w", encoding="utf-8").write(html)
open(LAND + "/js/push-1.js", "w").write(PUSH_JS)
print("\nAPPLIED - backups in", bak)
