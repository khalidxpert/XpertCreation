#!/usr/bin/env python3
# Notifications on phones and computers (web push) for everything that reaches the bell.
# Needs patch_chat.py applied first.
#   python3 /root/patch_push.py            dry run
#   python3 /root/patch_push.py --apply    write (backups in /root)
import os, re, sys, shutil, subprocess
from datetime import datetime
API = "/var/www/xpertcreation-api/notifications"
LAND = "/var/www/xpertcreation-landing"
APPLY = "--apply" in sys.argv
PUSH_PY = '"""Web push: phone and desktop notifications for everything that reaches the bell.\n\nnotify() in views.py calls send() after it writes the bell entry, so chat messages,\nconnection requests, endorsements, pet reminders and the rest all reach the phone.\nKeys: VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY and VAPID_SUBJECT in the environment or .env.\n"""\nimport json\nimport os\nimport threading\n\nfrom django.conf import settings\nfrom django.utils import timezone\nfrom rest_framework.decorators import api_view, permission_classes\nfrom rest_framework.permissions import AllowAny, IsAuthenticated\nfrom rest_framework.response import Response\n\nfrom .models import PushSubscription\n\nTITLES = {"chat_message": "New message", "connect": "Connect", "endorse": "Endorsement", "follow": "New follower",\n          "pet": "Your pet", "tick": "Blue tick", "report": "Report", "chat_report": "Chat report"}\n\n\ndef _env(name):\n    v = getattr(settings, name, "") or os.environ.get(name, "")\n    if v:\n        return v\n    base = getattr(settings, "BASE_DIR", "")\n    try:\n        with open(os.path.join(str(base), ".env")) as f:\n            for line in f:\n                if line.startswith(name + "="):\n                    return line.split("=", 1)[1].strip().strip(\'"\').strip("\'")\n    except OSError:\n        pass\n    return ""\n\n\ndef _payload(kind, text, link):\n    tag = "xc-" + (link or kind)\n    return json.dumps({"title": TITLES.get(kind, "XpertCreation"), "body": text[:180],\n                       "url": link or "/", "tag": tag})\n\n\ndef _deliver(sub_ids, data):\n    from pywebpush import WebPushException, webpush\n    key, subject = _env("VAPID_PRIVATE_KEY"), _env("VAPID_SUBJECT") or "mailto:admin@example.com"\n    if not key:\n        return\n    for s in PushSubscription.objects.filter(id__in=sub_ids):\n        try:\n            webpush(subscription_info={"endpoint": s.endpoint, "keys": {"p256dh": s.p256dh, "auth": s.auth}},\n                    data=data, vapid_private_key=key, vapid_claims={"sub": subject}, ttl=86400, timeout=6)\n            PushSubscription.objects.filter(id=s.id).update(last_ok=timezone.now(), fails=0)\n        except WebPushException as e:\n            code = getattr(getattr(e, "response", None), "status_code", 0)\n            if code in (404, 410):                      # the phone unsubscribed or the address expired\n                s.delete()\n            else:\n                PushSubscription.objects.filter(id=s.id).update(fails=s.fails + 1)\n        except Exception:\n            PushSubscription.objects.filter(id=s.id).update(fails=s.fails + 1)\n    PushSubscription.objects.filter(fails__gte=20).delete()\n\n\ndef send(user, kind, text, link=""):\n    """Queue a push for every device of this user. Never slows down or breaks the request."""\n    try:\n        ids = list(PushSubscription.objects.filter(user=user).values_list("id", flat=True))\n        if ids and _env("VAPID_PRIVATE_KEY"):\n            threading.Thread(target=_deliver, args=(ids, _payload(kind, text, link)), daemon=True).start()\n    except Exception:\n        pass\n\n\n@api_view(["GET"])\n@permission_classes([AllowAny])\ndef public_key(request):\n    return Response({"key": _env("VAPID_PUBLIC_KEY")})\n\n\n@api_view(["POST"])\n@permission_classes([IsAuthenticated])\ndef subscribe(request):\n    d = request.data or {}\n    endpoint = str(d.get("endpoint") or "")[:600]\n    keys = d.get("keys") or {}\n    if not endpoint.startswith("https://") or not keys.get("p256dh") or not keys.get("auth"):\n        return Response({"detail": "That subscription is not complete."}, status=400)\n    if PushSubscription.objects.filter(user=request.user).count() >= 10:\n        PushSubscription.objects.filter(user=request.user).order_by("created_at").first().delete()\n    PushSubscription.objects.update_or_create(endpoint=endpoint, defaults={\n        "user": request.user, "p256dh": str(keys["p256dh"])[:200], "auth": str(keys["auth"])[:100], "fails": 0})\n    return Response({"ok": True})\n\n\n@api_view(["POST"])\n@permission_classes([IsAuthenticated])\ndef unsubscribe(request):\n    PushSubscription.objects.filter(user=request.user, endpoint=str(request.data.get("endpoint") or "")[:600]).delete()\n    return Response({"ok": True})\n\n\n@api_view(["POST"])\n@permission_classes([IsAuthenticated])\ndef test(request):\n    send(request.user, "test", "Notifications are working. You will hear about new messages here.", "/chat")\n    return Response({"ok": True, "devices": PushSubscription.objects.filter(user=request.user).count()})\n'
MODEL_TAIL = '\n\nclass PushSubscription(models.Model):\n    """One phone or browser that agreed to get notifications."""\n    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_subscriptions")\n    endpoint = models.CharField(max_length=600, unique=True)\n    p256dh = models.CharField(max_length=200)\n    auth = models.CharField(max_length=100)\n    fails = models.PositiveSmallIntegerField(default=0)\n    created_at = models.DateTimeField(default=timezone.now)\n    last_ok = models.DateTimeField(null=True, blank=True)\n'
SW_ADD = '\n/* ---- push notifications: show them, and open the right page when tapped ---- */\nself.addEventListener("push", function(event){\n  var d = {};\n  try { d = event.data ? event.data.json() : {}; } catch (e) { d = {body: event.data ? event.data.text() : ""}; }\n  event.waitUntil(self.registration.showNotification(d.title || "XpertCreation", {\n    body: d.body || "", icon: "/brand/icon-512.png", badge: "/brand/logo-64.png",\n    tag: d.tag || "xc", renotify: true, data: {url: d.url || "/"}\n  }));\n});\nself.addEventListener("notificationclick", function(event){\n  event.notification.close();\n  var url = new URL((event.notification.data && event.notification.data.url) || "/", self.location.origin).href;\n  event.waitUntil(self.clients.matchAll({type: "window", includeUncontrolled: true}).then(function(list){\n    for (var i = 0; i < list.length; i++){\n      if (list[i].url === url && "focus" in list[i]) return list[i].focus();\n    }\n    return self.clients.openWindow ? self.clients.openWindow(url) : null;\n  }));\n});\n'
PUSH_JS = '/* Notifications on this phone or computer: the "Turn on" bar, and subscribe / unsubscribe.\n   Shows in any element with id="pushbar". */\n(function(){\n  "use strict";\n  var bar = document.getElementById("pushbar");\n  if (!bar) return;\n  var ok = "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;\n  function cookie(n){ var m = document.cookie.match("(^|;)\\\\s*" + n + "\\\\s*=\\\\s*([^;]+)"); return m ? m.pop() : ""; }\n  function post(p, body){\n    return fetch("/api/notify/push/" + p, {method: "POST", credentials: "same-origin",\n      headers: {"Content-Type": "application/json", "X-CSRFToken": cookie("xc_csrf")}, body: JSON.stringify(body || {})});\n  }\n  function b64(s){\n    var pad = "=".repeat((4 - s.length % 4) % 4), raw = atob((s + pad).replace(/-/g, "+").replace(/_/g, "/"));\n    var out = new Uint8Array(raw.length);\n    for (var i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);\n    return out;\n  }\n  function reg(){ return navigator.serviceWorker.register("/sw.js").then(function(){ return navigator.serviceWorker.ready; }); }\n  function box(html){\n    bar.innerHTML = html ? "<div style=\'display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:10px 0;padding:11px 14px;"\n      + "border:1px solid var(--line,#E4E8F2);border-radius:14px;background:var(--card,#fff);font-size:14px\'>" + html + "</div>" : "";\n  }\n  var BTN = "padding:7px 13px;border-radius:10px;font-weight:700;cursor:pointer;border:1px solid var(--line,#E4E8F2);";\n  function draw(){\n    if (!ok){ box(""); return; }\n    if (Notification.permission === "denied"){ box("\\uD83D\\uDD15 Notifications are blocked for this site. Allow them in your browser\'s site settings to hear about new messages."); return; }\n    reg().then(function(r){ return r.pushManager.getSubscription(); }).then(function(sub){\n      if (sub && Notification.permission === "granted"){\n        box(bar.getAttribute("data-quiet") ? "" : "\\uD83D\\uDD14 Notifications are on for this device. <span style=\'flex:1\'></span>"\n          + "<button data-push=\'test\' style=\'" + BTN + "background:var(--card,#fff)\'>Send a test</button>"\n          + "<button data-push=\'off\' style=\'" + BTN + "background:var(--card,#fff)\'>Turn off</button>");\n      } else {\n        box("\\uD83D\\uDD14 Get a notification on this device when someone messages you. <span style=\'flex:1\'></span>"\n          + "<button data-push=\'on\' style=\'" + BTN + "background:var(--brand,#1B4DFF);color:#fff;border-color:var(--brand,#1B4DFF)\'>Turn on</button>");\n      }\n    }).catch(function(){ box(""); });\n  }\n  bar.addEventListener("click", function(e){\n    var b = e.target.closest("[data-push]");\n    if (!b) return;\n    var what = b.getAttribute("data-push");\n    b.disabled = true;\n    if (what === "on"){\n      Notification.requestPermission().then(function(p){\n        if (p !== "granted") return draw();\n        return fetch("/api/notify/push/key/").then(function(r){ return r.json(); }).then(function(k){\n          if (!k.key) throw new Error("no key");\n          return reg().then(function(r){ return r.pushManager.subscribe({userVisibleOnly: true, applicationServerKey: b64(k.key)}); });\n        }).then(function(sub){ return post("subscribe/", sub.toJSON()); }).then(draw);\n      }).catch(function(){ b.disabled = false; alert("Could not turn on notifications on this device."); });\n    } else if (what === "off"){\n      reg().then(function(r){ return r.pushManager.getSubscription(); }).then(function(sub){\n        if (!sub) return;\n        return post("unsubscribe/", {endpoint: sub.endpoint}).then(function(){ return sub.unsubscribe(); });\n      }).then(draw);\n    } else if (what === "test"){\n      post("test/").then(function(){ b.textContent = "Sent \\u2713"; });\n    }\n  });\n  fetch("/api/auth/me/", {credentials: "same-origin"}).then(function(r){ if (r.ok) draw(); }).catch(function(){});\n})();\n'

fail = []
def need(label, ok):
    print("  %-40s %s" % (label, "ok" if ok else "PROBLEM"))
    if not ok: fail.append(label)

V, U, M, A = API + "/views.py", API + "/urls.py", API + "/models.py", API + "/admin.py"
v, u, m = open(V).read(), open(U).read(), open(M).read()
a = open(A).read() if os.path.exists(A) else "from django.contrib import admin\n"
need("chat part 1 is applied (patch_chat.py)", "def thread_typing" in v)
need("push not added yet", not os.path.exists(API + "/push.py") and "PushSubscription" not in m)
A_N = "    Notification.objects.create(user=user, kind=kind, text=text[:200], link=link[:200])\n"
need("views: notify() line", v.count(A_N) == 1)
v2 = v.replace(A_N, A_N + "    try:\n        from .push import send as _push\n        _push(user, kind, text, link)\n    except Exception:\n        pass\n", 1)
A_U1, A_U2 = "from . import views\n", '    path("threads/", views.my_threads, name="threads"),\n'
need("urls anchors", u.count(A_U1) == 1 and u.count(A_U2) == 1)
u2 = u.replace(A_U1, "from . import push, views\n", 1).replace(A_U2,
    '    path("push/key/", push.public_key, name="push-key"),\n'
    '    path("push/subscribe/", push.subscribe, name="push-subscribe"),\n'
    '    path("push/unsubscribe/", push.unsubscribe, name="push-unsubscribe"),\n'
    '    path("push/test/", push.test, name="push-test"),\n' + A_U2, 1)
m2 = m.rstrip("\n") + "\n" + MODEL_TAIL
a2 = a if "PushSubscription" in a else a.rstrip("\n") + ("\n\nfrom django.contrib import admin as _padmin\nfrom .models import PushSubscription as _Push\n\n\n"
    "@_padmin.register(_Push)\nclass PushSubscriptionAdmin(_padmin.ModelAdmin):\n"
    '    list_display = ("user", "created_at", "last_ok", "fails")\n    readonly_fields = ("endpoint", "p256dh", "auth")\n')
for n, s in (("views.py", v2), ("urls.py", u2), ("models.py", m2), ("admin.py", a2), ("push.py", PUSH_PY)):
    try: compile(s, n, "exec"); ok = True
    except SyntaxError as e: print("   ", e); ok = False
    need("python parses " + n, ok)

SW = LAND + "/sw.js"
sw = open(SW).read()
need("sw.js: no push handler yet", "notificationclick" not in sw)
sw2 = sw.rstrip("\n") + "\n" + SW_ADD
TAG = '<script src="/js/push-1.js" defer></script>'
pages = {}
for name, anchor, bar in (("chat.html", '  <h1>Chat</h1>\n  <div id="list5"', '  <h1>Chat</h1>\n  <div id="pushbar"></div>\n  <div id="list5"'),
                          ("index.html", '<div id="recentchats"></div>', '<div id="pushbar" data-quiet="1"></div>\n<div id="recentchats"></div>')):
    s = open(LAND + "/" + name, encoding="utf-8").read()
    tn = re.search(r'<script src="/js/topnav-1\.js(\?v=\d+)?" defer></script>', s)
    need(name + ": pushbar spot", s.count(anchor) == 1)
    need(name + ": menu script tag", bool(tn))
    if s.count(anchor) == 1 and tn and "push-1.js" not in s:
        s = s.replace(anchor, bar, 1)
        s = s[:tn.end()] + "\n" + TAG + s[tn.end():]
    pages[LAND + "/" + name] = s
open("/tmp/pp.js", "w").write(PUSH_JS)
need("node --check push-1.js", subprocess.run(["node", "--check", "/tmp/pp.js"], capture_output=True).returncode == 0)
open("/tmp/pp.js", "w").write(sw2)
need("node --check sw.js", subprocess.run(["node", "--check", "/tmp/pp.js"], capture_output=True).returncode == 0)
if fail:
    sys.exit("\nSTOP - " + ", ".join(fail) + ". Nothing written.")
if not APPLY:
    print("\nDRY RUN OK - nothing written. Run again with --apply."); sys.exit(0)
bak = "/root/push_bak_" + datetime.now().strftime("%Y%m%d_%H%M%S")
os.makedirs(bak)
for p in [V, U, M, SW] + list(pages) + ([A] if os.path.exists(A) else []):
    shutil.copy(p, bak + "/" + os.path.basename(p))
open("/tmp/push_bakdir", "w").write(bak)
open(V, "w").write(v2); open(U, "w").write(u2); open(M, "w").write(m2); open(A, "w").write(a2)
open(API + "/push.py", "w").write(PUSH_PY); open(SW, "w").write(sw2)
open(LAND + "/js/push-1.js", "w").write(PUSH_JS)
for p, s in pages.items():
    open(p, "w", encoding="utf-8").write(s)
print("\nAPPLIED - backups in", bak)
