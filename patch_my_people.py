#!/usr/bin/env python3
# /me/profile: "followers", "following" and "connections" become links that open the list,
# with a Message button next to each connection. New endpoint /api/network/me/people/<which>/.
#   python3 /root/patch_my_people.py            dry run
#   python3 /root/patch_my_people.py --apply    write (backups in /root)
import os, re, sys, shutil, subprocess
from datetime import datetime

API = os.environ.get("API", "/var/www/xpertcreation-api")
ME = os.environ.get("ME", "/var/www/xpertcreation-landing/me-profile.html")
VIEWS, URLS = API + "/network/views.py", API + "/network/urls.py"
APPLY = "--apply" in sys.argv

VIEW = '''

@api_view(["GET"])
@permission_classes([IsAuthenticated])
@throttle_classes([EditThrottle])
def my_people(request, which):
    """The signed-in member's connections, followers, or the people they follow."""
    me_ = request.user
    if which == "connections":
        rows = (Connection.objects.filter(Q(from_user=me_) | Q(to_user=me_), state=Connection.ACCEPTED)
                .select_related("from_user", "to_user").order_by("-responded_at"))
        users = [c.to_user if c.from_user_id == me_.pk else c.from_user for c in rows]
    elif which == "followers":
        users = [f.follower for f in Follow.objects.filter(following=me_).select_related("follower").order_by("-created_at")]
    elif which == "following":
        users = [f.following for f in Follow.objects.filter(follower=me_).select_related("following").order_by("-created_at")]
    else:
        return _err("Unknown list.", 404)
    users = [u for u in users if u.is_active and not u.is_blocked][:500]
    out = []
    for u in users:
        # Connections always get a profile, so the Message button has somewhere to go.
        p = _get_or_make(u) if which == "connections" else ProProfile.objects.filter(user=u).first()
        out.append({"user_id": u.pk, "name": _name(u), "avatar_url": _av(u),
                    "slug": p.slug if p else None, "headline": p.headline if p else "",
                    "verified": _ticked(p) if p else False})
    return Response({"which": which, "people": out})
'''
A_URL = '    path("me/tick/", views.tick_apply, name="net-tick"),\n'
N_URL = A_URL + '    path("me/people/<str:which>/", views.my_people, name="net-my-people"),\n'

A_LEAD = '"</a> \\u00b7 <b>" + P.followers + "</b> followers \\u00b7 <b>" + P.connections + "</b> connections";'
N_LEAD = ('"</a> \\u00b7 <a href=\'#plist\' data-list=\'followers\'><b>" + P.followers + "</b> followers</a>'
          ' \\u00b7 <a href=\'#plist\' data-list=\'following\'><b>" + P.following + "</b> following</a>'
          ' \\u00b7 <a href=\'#plist\' data-list=\'connections\'><b>" + P.connections + "</b> connections</a>";')
A_BODY = '  <div id="requests"></div>\n  <div id="main"></div>'
N_BODY = '  <div id="requests"></div>\n  <div id="plist"></div>\n  <div id="main"></div>'
A_JS = '  fetch("/api/auth/csrf/", {credentials: "same-origin"}).catch(function(){});'
N_JS = r"""  // Followers, following and connections open as a list, with Message beside each connection.
  function showPeople(which){
    var box = document.getElementById("plist");
    if (!box) return;
    box.innerHTML = "<p class='muted'>Loading\u2026</p>";
    api("/me/people/" + which + "/").then(function(r){
      if (!r.ok){ box.innerHTML = "<p class='msg bad'>" + esc(r.data.detail || "Could not load.") + "</p>"; return; }
      var title = {followers: "Your followers", following: "People you follow", connections: "Your connections"}[which];
      var list = r.data.people || [];
      box.innerHTML = "<h2>" + title + " (" + list.length + ")</h2><div class='card'>" + (list.length ? list.map(function(p){
        var name = p.slug ? "<a href='/in/" + encodeURIComponent(p.slug) + "' style='color:inherit'>" + esc(p.name) + "</a>" : esc(p.name);
        return "<div class='sk'><div style='display:flex;gap:10px;align-items:center;min-width:0'>" + avatar(p)
          + "<div><b>" + name + "</b>" + tick(p.verified) + "<div class='muted'>" + esc(p.headline || "") + "</div></div></div>"
          + (which === "connections" && p.slug ? "<button class='btn sm pri' data-msg='" + esc(p.slug) + "'>Message</button>" : "")
          + "</div>";
      }).join("") : "<p class='muted' style='margin:0'>Nobody here yet.</p>") + "</div>";
      box.scrollIntoView({behavior: "smooth"});
    });
  }
  document.addEventListener("click", function(e){
    var a = e.target.closest("[data-list]");
    if (a){ e.preventDefault(); showPeople(a.getAttribute("data-list")); return; }
    var m = e.target.closest("[data-msg]");
    if (m){
      m.disabled = true;
      api("/in/" + encodeURIComponent(m.getAttribute("data-msg")) + "/message/", {method: "POST", body: {}}).then(function(r){
        if (r.ok){ location.href = "/chat/" + r.data.id; return; }
        m.disabled = false;
        alert(r.data.detail || "Could not open the chat.");
      });
    }
  });
  if (/^#(connections|followers|following)$/.test(location.hash)) setTimeout(function(){ showPeople(location.hash.slice(1)); }, 400);

"""

fail = []
def need(label, ok):
    print("  %-32s %s" % (label, "ok" if ok else "PROBLEM"))
    if not ok: fail.append(label)

v, u, h = open(VIEWS).read(), open(URLS).read(), open(ME, encoding="utf-8").read()
need("urls anchor (me/tick)", u.count(A_URL) == 1)
need("view not there yet", "def my_people" not in v)
need("views has _ticked and Follow", "def _ticked" in v and "Follow" in v)
need("profile lead anchor", h.count(A_LEAD) == 1)
need("profile body anchor", h.count(A_BODY) == 1)
need("profile js anchor", h.count(A_JS) == 1)
v2, u2 = v.rstrip("\n") + "\n" + VIEW, u.replace(A_URL, N_URL, 1)
h2 = h.replace(A_LEAD, N_LEAD, 1).replace(A_BODY, N_BODY, 1).replace(A_JS, N_JS + A_JS, 1)
for n, s in (("views.py", v2), ("urls.py", u2)):
    try: compile(s, n, "exec"); ok = True
    except SyntaxError as e: print("   ", e); ok = False
    need("python parses " + n, ok)
bad = []
for k, b in enumerate(re.findall(r"<script>(.*?)</script>", h2, re.S)):
    open("/tmp/mpp_%d.js" % k, "w", encoding="utf-8").write(b)
    r = subprocess.run(["node", "--check", "/tmp/mpp_%d.js" % k], capture_output=True, text=True)
    if r.returncode: bad.append(r.stderr[:300])
need("node --check me-profile.html", not bad)
for b in bad: print(b)
if fail:
    sys.exit("\nSTOP - %s. Nothing written." % ", ".join(fail))
if not APPLY:
    print("\nDRY RUN OK - nothing written. Run again with --apply."); sys.exit(0)
bak = "/root/my_people_bak_" + datetime.now().strftime("%Y%m%d_%H%M%S")
os.makedirs(bak)
for p in (VIEWS, URLS, ME): shutil.copy(p, bak)
open("/tmp/my_people_bakdir", "w").write(bak)
open(VIEWS, "w").write(v2); open(URLS, "w").write(u2); open(ME, "w", encoding="utf-8").write(h2)
print("\nAPPLIED - backups in", bak)
