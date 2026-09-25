#!/bin/bash
# patch_video_polish.sh
#
#   Three things to finish the video library:
#
#   1. Bigger cards. Thumbnail on top at full width, two or three to a
#      row - it now looks like a video library, not a list of links.
#
#   2. A preview in the moderation queue. Deciding on a title alone is
#      not moderating; now the video plays right there in the queue.
#
#   3. A badge on the main homepage, under the Moderation bar, showing
#      how many videos are waiting. Tapping it opens the queue, so
#      nobody has to remember the address.
#
#   Touches three files: accounts/views.py (the count), the homepage
#   (the badge), and the academy page (cards and preview). Each is
#   checked before it is written, and all three are backed up.
#
# First:  bash patch_video_polish.sh --dry-run
# Then:   bash patch_video_polish.sh

set -u

ACC=/var/www/xpertcreation-api/accounts/views.py
HOME_=/var/www/xpertcreation-landing/index.html
ACAD=/var/www/xpertacademy/index.html
SW=/var/www/xpertcreation-landing/sw.js

DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

echo "=============================================================="
[ $DRY -eq 1 ] && echo "DRY RUN - nothing will be written" || echo "LIVE"
echo "=============================================================="

for f in "$ACC" "$HOME_" "$ACAD" "$SW"; do
  [ -f "$f" ] || { echo "NOT FOUND: $f"; exit 1; }
done

python3 - "$ACC" "$HOME_" "$ACAD" "$DRY" <<'PYEOF'
import ast, os, re, shutil, subprocess, sys, tempfile
from datetime import datetime

ACC, HOME_, ACAD, DRY = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] == "1"
acc = open(ACC, encoding="utf-8").read()
home = open(HOME_, encoding="utf-8").read()
acad = open(ACAD, encoding="utf-8").read()

if "data-vqplay" in acad:
    print("\nAlready done. Nothing changed.")
    sys.exit(0)

fail = []

# ---------------------------------------------- 1. the count, server side
A_OLD = '        "pending": pending,\n    })'
n = acc.count(A_OLD)
print("\n[1] my_role response".ljust(40), n, "match")
if n != 1:
    fail.append("my_role response found %d times, need 1" % n)
else:
    A_NEW = ('        "pending": pending,\n'
             '        "videos": videos,\n'
             '    })')
    acc = acc.replace(A_OLD, A_NEW, 1)

B_OLD = ('        pending = Review.objects.filter(state=Review.PENDING)'
         '.exclude(comment="").count()')
n = acc.count(B_OLD)
print("[2] pending count".ljust(40), n, "match")
if n != 1:
    fail.append("pending count found %d times, need 1" % n)
else:
    B_NEW = B_OLD + '''
        # Videos sent to a course, waiting to be looked at. Counted
        # here so the homepage can say so without a second request.
        try:
            from academy.models import VideoPost
            videos = VideoPost.objects.filter(state=VideoPost.PENDING).count()
        except Exception:
            videos = 0'''
    acc = acc.replace(B_OLD, B_NEW, 1)
    # and a default for everyone who is not a moderator
    acc = acc.replace("    pending = 0\n    if u.is_moderator or u.is_superuser:",
                      "    pending = 0\n    videos = 0\n    if u.is_moderator or u.is_superuser:", 1)
    if "    videos = 0\n    if u.is_moderator" not in acc:
        fail.append("could not set the videos default")

# ---------------------------------------------- 2. the homepage badge
C_OLD = '''      if (d.pending){
        var c = document.getElementById("modcnt");
        c.textContent = d.pending + " waiting";
        c.hidden = false;
      }'''
n = home.count(C_OLD)
print("[3] homepage moderation badge".ljust(40), n, "match")
if n != 1:
    fail.append("homepage badge found %d times, need 1" % n)
else:
    C_NEW = C_OLD + '''
      // Videos waiting get their own bar, pointing straight at the
      // queue - nobody should have to remember that address.
      if (d.videos){
        var v = document.createElement("a");
        v.className = "modbar on";
        v.href = "/academy/?v=vqueue";
        v.innerHTML = '<span class="e5">&#127909;</span>'
          + '<span class="t"><b>Videos</b>'
          + '<small>Sent to a course, waiting to be checked</small></span>'
          + '<span class="cnt2">' + Number(d.videos) + ' waiting</span>';
        bar.parentNode.insertBefore(v, bar.nextSibling);
      }'''
    home = home.replace(C_OLD, C_NEW, 1)

# ---------------------------------------------- 3. bigger cards
D_OLD = ".runner{margin:14px 0;border-radius:14px;overflow:hidden;"
n = acad.count(D_OLD)
print("[4] runner CSS (anchor)".ljust(40), n, "match")
if n != 1:
    fail.append("runner CSS found %d times, need 1" % n)
else:
    D_NEW = """/* Bigger video cards. Thumbnail on top at full width, two or three
   to a row - a video library should look like one. */
.vwrap{grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:14px}
.vwrap .vdim{grid-column:1 / -1}
.vcard{grid-template-columns:1fr}
.vthumb{aspect-ratio:16/9;min-height:0;width:100%}
.vgo{width:58px;height:58px;font-size:20px}
.vcard .vtitle{font-size:15px}
.vcard.vq{grid-template-columns:1fr}

""" + D_OLD
    acad = acad.replace(D_OLD, D_NEW, 1)

# ---------------------------------------------- 4. preview in the queue
E_OLD = """        return '<div class="vcard vq" data-vid="' + v.id + '">'
          + '<div class="vbody">'"""
n = acad.count(E_OLD)
print("[5] queue card".ljust(40), n, "match")
if n != 1:
    fail.append("queue card found %d times, need 1" % n)
else:
    E_NEW = """        return '<div class="vcard vq" data-vid="' + v.id + '">'
          + '<button class="vthumb" data-vqplay="' + esc(v.embed) + '"'
          + (v.thumb ? ' style="background-image:url(' + esc(v.thumb) + ')"' : '')
          + '><span class="vgo">\\u25b6</span></button>'
          + '<div class="vbody">'"""
    acad = acad.replace(E_OLD, E_NEW, 1)

F_OLD = "  function lessonFor(c, i){"
n = acad.count(F_OLD)
print("[6] lessonFor (anchor)".ljust(40), n, "match")
if n != 1:
    fail.append("lessonFor found %d times, need 1" % n)
else:
    F_NEW = """  /* In the queue a thumbnail becomes the player when tapped, so a
     moderator watches the video instead of judging it by its title. */
  document.addEventListener("click", function(e){
    var b = e.target.closest ? e.target.closest("[data-vqplay]") : null;
    if (!b) return;
    var d = document.createElement("div");
    d.className = "vplay";
    d.innerHTML = '<iframe src="' + esc(b.getAttribute("data-vqplay"))
      + '?rel=0" loading="lazy" allowfullscreen '
      + 'allow="accelerometer; encrypted-media; picture-in-picture" '
      + 'referrerpolicy="strict-origin-when-cross-origin"></iframe>';
    b.replaceWith(d);
  });

""" + F_OLD
    acad = acad.replace(F_OLD, F_NEW, 1)

if fail:
    print("\nSTOPPED - nothing written:")
    for f in fail:
        print("  -", f)
    sys.exit(1)

# ---------------------------------------------- checks before writing
try:
    ast.parse(acc)
    print("\naccounts/views.py: parses")
except SyntaxError as e:
    print("\nSTOPPED - accounts/views.py line %s: %s" % (e.lineno, e.msg))
    sys.exit(1)

def js_ok(name, text):
    scripts = re.findall(r'<script(?![^>]*type=)[^>]*>(.*?)</script>', text, re.S)
    ok = tot = 0
    for sc in scripts:
        if not sc.strip():
            continue
        tot += 1
        tf = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                         encoding="utf-8")
        tf.write(sc); tf.close()
        r = subprocess.run(["node", "--check", tf.name],
                           capture_output=True, text=True)
        os.unlink(tf.name)
        if r.returncode == 0:
            ok += 1
    print("%s: node --check %d/%d" % (name, ok, tot))
    return ok == tot

if not (js_ok("homepage", home) and js_ok("academy", acad)):
    print("\nSTOPPED - a script would not parse. Nothing written.")
    sys.exit(1)

if DRY:
    print("\nDRY RUN over. Run again without --dry-run.")
    sys.exit(0)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
for path, text, tag in ((ACC, acc, "acc-views"), (HOME_, home, "home-index"),
                        (ACAD, acad, "academy-index")):
    b = "/root/%s.bakpol_%s" % (tag, stamp)
    shutil.copy2(path, b)
    open(path, "w", encoding="utf-8").write(text)
    print("  %-26s backup: %s" % (os.path.basename(path), os.path.basename(b)))
PYEOF

rc=$?
cd /root
if [ $rc -ne 0 ]; then
  echo
  echo "Stopped. Reason above."
  exit $rc
fi

if [ $DRY -eq 1 ]; then
  exit 0
fi

echo
echo "Restarting the API:"
systemctl restart gunicorn-academy && systemctl is-active gunicorn-academy

echo
echo "Service worker, so browsers pick this up:"
sed -i 's/const VERSION = "xc-v[0-9]*";/const VERSION = "xc-v5";/' "$SW"
grep -n "const VERSION" "$SW"

echo
echo "Close every tab of the site and open it again."
echo "Send a test video, and the homepage should show a Videos bar."

cd /root
