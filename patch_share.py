#!/usr/bin/env python3
# Share buttons (phone share sheet, WhatsApp, Facebook, X, LinkedIn, Telegram, Copy link) at the bottom of
# profiles, pet tags, lost and found, shows, tools (and every tool page), games, business and the guide.
#   python3 /root/patch_share.py            dry run
#   python3 /root/patch_share.py --apply    write
import os, glob, shutil
from datetime import datetime
LAND = "/var/www/xpertcreation-landing"
APPLY = "--apply" in os.sys.argv
JS = '/* Share buttons at the bottom of a page: the phone\'s own share sheet, WhatsApp, Facebook, X, LinkedIn,\n   Telegram and Copy link. Uses the page\'s address at the moment of tapping, so tools opened with ?t=...\n   share the right tool. */\n(function(){\n  "use strict";\n  var host = document.querySelector(".wrap") || document.querySelector("main") || document.body;\n  if (!host || document.getElementById("xshare")) return;\n  var css = document.createElement("style");\n  css.textContent = ".xshare{margin:22px 0 8px;padding:14px 16px;border:1px solid var(--line,#E4E8F2);border-radius:18px;background:var(--card,#fff)}" +\n    ".xshare b{display:block;font-size:14px;margin-bottom:10px;color:var(--ink,#0D1424)}" +\n    ".xshare .row{display:flex;gap:8px;flex-wrap:wrap}" +\n    ".xshare a,.xshare button{display:inline-flex;align-items:center;gap:6px;padding:9px 13px;border-radius:11px;border:0;" +\n    "font:inherit;font-size:13.5px;font-weight:700;color:#fff;text-decoration:none;cursor:pointer}" +\n    ".xshare .wa{background:#25D366}.xshare .fb{background:#1877F2}.xshare .x{background:#111}" +\n    ".xshare .li{background:#0A66C2}.xshare .tg{background:#229ED9}" +\n    ".xshare .cp,.xshare .nat{background:var(--paper,#F6F7FB);color:var(--ink,#0D1424);border:1px solid var(--line,#E4E8F2)}";\n  document.head.appendChild(css);\n  var box = document.createElement("div");\n  box.className = "xshare";\n  box.id = "xshare";\n  box.innerHTML = "<b>Share this page</b><div class=\'row\'>"\n    + (navigator.share ? "<button type=\'button\' class=\'nat\' data-s=\'native\'>\\u2197\\uFE0F Share</button>" : "")\n    + "<a class=\'wa\' data-s=\'wa\' href=\'#\' target=\'_blank\' rel=\'noopener\'>WhatsApp</a>"\n    + "<a class=\'fb\' data-s=\'fb\' href=\'#\' target=\'_blank\' rel=\'noopener\'>Facebook</a>"\n    + "<a class=\'x\' data-s=\'x\' href=\'#\' target=\'_blank\' rel=\'noopener\'>X</a>"\n    + "<a class=\'li\' data-s=\'li\' href=\'#\' target=\'_blank\' rel=\'noopener\'>LinkedIn</a>"\n    + "<a class=\'tg\' data-s=\'tg\' href=\'#\' target=\'_blank\' rel=\'noopener\'>Telegram</a>"\n    + "<button type=\'button\' class=\'cp\' data-s=\'copy\'>\\uD83D\\uDD17 Copy link</button></div>";\n  host.appendChild(box);\n  box.addEventListener("click", function(e){\n    var el = e.target.closest("[data-s]");\n    if (!el) return;\n    var url = location.href.split("#")[0], title = document.title.replace(/\\s+\\u2014\\s+XpertCreation.*$/, "");\n    var u = encodeURIComponent(url), t = encodeURIComponent(title);\n    var links = {\n      wa: "https://wa.me/?text=" + encodeURIComponent(title + " " + url),\n      fb: "https://www.facebook.com/sharer/sharer.php?u=" + u,\n      x: "https://x.com/intent/tweet?url=" + u + "&text=" + t,\n      li: "https://www.linkedin.com/sharing/share-offsite/?url=" + u,\n      tg: "https://t.me/share/url?url=" + u + "&text=" + t\n    };\n    var s = el.getAttribute("data-s");\n    if (links[s]){ el.href = links[s]; return; }          // the link opens in a new tab by itself\n    e.preventDefault();\n    if (s === "native") navigator.share({title: title, url: url}).catch(function(){});\n    if (s === "copy"){\n      var done = function(){ el.textContent = "\\u2713 Copied"; setTimeout(function(){ el.textContent = "\\uD83D\\uDD17 Copy link"; }, 1800); };\n      if (navigator.clipboard) navigator.clipboard.writeText(url).then(done, function(){ prompt("Copy this link:", url); });\n      else prompt("Copy this link:", url);\n    }\n  });\n})();\n'
TAG = '<script src="/js/share-1.js" defer></script>\n'
NAMES = ["in.html", "pet.html", "lost.html", "show.html", "shows.html", "tools.html", "games.html", "arrows.html", "ludo.html",
         "chess.html", "business.html", "zodiac.html", "blood.html", "people.html", "team.html"]
todo = []
for n in NAMES:
    p = LAND + "/" + n
    if not os.path.exists(p):
        print("  %-14s not on this site, skipped" % n); continue
    s = open(p, encoding="utf-8").read()
    if "share-1.js" in s or s.rfind("</body>") < 0:
        print("  %-14s already has it" % n); continue
    todo.append((p, s))
    print("  %-14s will get share buttons" % n)
if not APPLY:
    print("DRY RUN OK - nothing written. Run again with --apply."); raise SystemExit
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
os.makedirs(LAND + "/js", exist_ok=True)
open(LAND + "/js/share-1.js", "w").write(JS)
for p, s in todo:
    shutil.copy(p, "/root/" + os.path.basename(p) + ".bak_" + stamp)
    i = s.rfind("</body>")
    open(p, "w", encoding="utf-8").write(s[:i] + TAG + s[i:])
print("APPLIED - %d pages; backups /root/*.bak_%s" % (len(todo), stamp))
