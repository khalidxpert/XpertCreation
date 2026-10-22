/* My Briefcase (XpertCreation) - your own documents, encrypted on our server, only you can open them.
   Folders, add by XpertScan or upload, expiry reminders, download as PDF / JPG / PNG, combine into one PDF,
   share a link that ends by itself. */
(function(){
  "use strict";
  var D = document, B = D.body, API = "/api/brief/";
  var S = {folders: [], docs: [], used: 0, limit: 1, max_file: 8388608, view: "home", folder: null, pick: null};
  var ICONS = ["📂", "💼", "🎓", "🏦", "🚗", "✈️", "👶", "💍", "💳", "🧾", "🏢", "⭐"];
  var MONTH = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  function esc(s){ return String(s == null ? "" : s).replace(/[&<>"']/g, function(c){ return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]; }); }
  function ck(n){ var m = D.cookie.match(new RegExp("(?:^|; )" + n + "=([^;]*)")); return m ? decodeURIComponent(m[1]) : ""; }
  function req(method, url, body){
    var o = {method: method, credentials: "same-origin", headers: {"X-CSRFToken": ck("xc_csrf")}};
    if (body instanceof FormData) o.body = body;
    else if (body){ o.body = JSON.stringify(body); o.headers["Content-Type"] = "application/json"; }
    return fetch(API + url, o).then(function(r){
      return r.json().catch(function(){ return {}; }).then(function(d){
        if (r.status === 401 || r.status === 403){ var e = new Error("signin"); e.signin = true; throw e; }
        if (!r.ok) throw new Error(d.detail || (r.status === 413 ? "That file is too big (8 MB at most)." : "Something went wrong. Try again."));
        return d;
      });
    });
  }
  function mb(n){ if (!n) return "0 KB"; return n >= 1048576 ? (n / 1048576).toFixed(1) + " MB" : Math.max(1, Math.round(n / 1024)) + " KB"; }
  function nice(iso){ if (!iso) return ""; var p = iso.split("-"); return +p[2] + " " + MONTH[+p[1] - 1] + " " + p[0]; }
  function isImg(d){ return /^image\//.test(d.mime); }
  function isPdf(d){ return d.mime === "application/pdf"; }
  function kindIcon(d){ return isPdf(d) ? "📄" : isImg(d) ? "🖼️" : /word/.test(d.mime) ? "📝" : /sheet|excel/.test(d.mime) ? "📊" : /presentation/.test(d.mime) ? "📽️" : "📎"; }
  function badge(d){
    if (d.days_left == null) return "";
    var t = d.days_left < 0 ? "Expired " + nice(d.expires) : d.days_left === 0 ? "Expires today" : d.days_left <= 60 ? "Expires in " + d.days_left + " day" + (d.days_left === 1 ? "" : "s") : "Valid till " + nice(d.expires);
    var c = d.days_left < 0 || d.days_left <= 7 ? "red" : d.days_left <= 60 ? "amber" : "ok";
    return '<span class="bc-badge ' + c + '">' + esc(t) + "</span>";
  }
  function folderOf(key){ for (var i = 0; i < S.folders.length; i++) if (S.folders[i].key === key) return S.folders[i]; return {key: key, name: "Other", icon: "📁"}; }
  function toast(t){ var e = D.createElement("div"); e.className = "bc-toast"; e.textContent = t; B.appendChild(e); setTimeout(function(){ e.classList.add("on"); }, 10); setTimeout(function(){ e.remove(); }, 2600); }

  /* ------------------------------------------------------------ css */
  var css = D.createElement("style");
  css.textContent = [
    ".bc{max-width:640px;margin:0 auto;padding:16px 15px 110px}",
    ".bc h1{font-size:26px;font-weight:900;letter-spacing:-.03em;margin:4px 0 2px}",
    ".bc .ur{font-family:'Noto Nastaliq Urdu','Jameel Noori Nastaleeq',serif;direction:rtl;color:#5A657C;font-size:15px}",
    ".bc .lead{color:#5A657C;font-size:13.5px;margin:6px 0 12px}",
    ".bc-lock{display:flex;gap:10px;align-items:center;background:#EEF7F2;border:1px solid #CDEBDC;color:#0B6B47;border-radius:14px;padding:10px 12px;font-size:12.5px;margin-bottom:14px}",
    ".bc-use{height:6px;border-radius:9px;background:#E4E8F2;overflow:hidden;margin:4px 0 2px}.bc-use i{display:block;height:100%;background:#1B4DFF}",
    ".bc-usetx{font-size:11.5px;color:#5A657C;margin-bottom:14px}",
    ".bc-sec{font-size:12px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:#5A657C;margin:18px 0 8px}",
    ".bc-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}@media(min-width:520px){.bc-grid{grid-template-columns:repeat(3,1fr)}}",
    ".bc-f{background:#fff;border:1px solid #E4E8F2;border-radius:18px;padding:14px;text-align:left;cursor:pointer;font:inherit;color:inherit;display:flex;flex-direction:column;gap:2px;min-height:108px}",
    ".bc-f:active{transform:scale(.98)}.bc-f .e{font-size:30px;line-height:1}.bc-f b{font-size:14px;margin-top:8px}.bc-f small{font-size:12px;color:#5A657C}.bc-f .u{font-size:12.5px;color:#5A657C;direction:rtl;text-align:right}",
    ".bc-f.new{border-style:dashed;align-items:center;justify-content:center;color:#1B4DFF;font-weight:800}",
    ".bc-row{display:flex;gap:12px;align-items:center;background:#fff;border:1px solid #E4E8F2;border-radius:16px;padding:10px;margin-bottom:8px;cursor:pointer}",
    ".bc-row .th{width:54px;height:54px;border-radius:12px;background:#F1F4FA;flex:0 0 auto;display:grid;place-items:center;font-size:26px;overflow:hidden}",
    ".bc-row .th img{width:100%;height:100%;object-fit:cover}",
    ".bc-row .t{flex:1;min-width:0}.bc-row .t b{display:block;font-size:14.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.bc-row .t small{display:block;font-size:12px;color:#5A657C}",
    ".bc-row .ck{width:24px;height:24px;border-radius:8px;border:2px solid #C9D1E3;flex:0 0 auto;display:none;place-items:center;color:#fff;font-weight:900}",
    ".bc.sel .bc-row .ck{display:grid}.bc-row.on .ck{background:#1B4DFF;border-color:#1B4DFF}",
    ".bc-badge{display:inline-block;font-size:11px;font-weight:800;padding:2px 8px;border-radius:99px;margin-top:3px}",
    ".bc-badge.red{background:#FDE8E8;color:#B91C1C}.bc-badge.amber{background:#FEF3C7;color:#92400E}.bc-badge.ok{background:#E8F7EF;color:#0B6B47}",
    ".bc-back{background:none;border:0;color:#1B4DFF;font:inherit;font-weight:800;font-size:14px;padding:4px 0;cursor:pointer}",
    ".bc-head{display:flex;align-items:center;gap:8px;margin:8px 0 12px}.bc-head h2{flex:1;font-size:21px;margin:0}",
    ".bc-btn{border:0;border-radius:13px;padding:11px 16px;font:inherit;font-weight:800;font-size:14px;cursor:pointer;background:#0D1424;color:#fff}",
    ".bc-btn.ghost{background:#fff;color:#0D1424;border:1px solid #E4E8F2}.bc-btn.blue{background:#1B4DFF}.bc-btn.red{background:#fff;color:#DC2626;border:1px solid #F3C4C4}",
    ".bc-btn:disabled{opacity:.5}",
    ".bc-fab{position:fixed;right:18px;bottom:84px;z-index:30;background:#1B4DFF;color:#fff;border:0;border-radius:99px;padding:15px 22px;font:inherit;font-weight:800;font-size:15px;box-shadow:0 10px 26px rgba(27,77,255,.35);cursor:pointer}",
    ".bc-bar{position:fixed;left:0;right:0;bottom:0;z-index:35;background:#fff;border-top:1px solid #E4E8F2;padding:10px 14px calc(10px + env(safe-area-inset-bottom));display:flex;gap:8px;justify-content:center;flex-wrap:wrap}",
    ".bc-empty{text-align:center;color:#5A657C;padding:30px 10px;font-size:14px}",
    ".bc-sh{position:fixed;inset:0;z-index:2147483000;background:rgba(13,20,36,.5);display:flex;align-items:flex-end;justify-content:center}",
    ".bc-box{background:#fff;width:100%;max-width:560px;max-height:92vh;overflow:auto;border-radius:22px 22px 0 0;padding:10px 18px calc(18px + env(safe-area-inset-bottom))}",
    "@media(min-width:700px){.bc-sh{align-items:center}.bc-box{border-radius:22px}}",
    ".bc-grab{width:44px;height:5px;border-radius:9px;background:#D6DCE8;margin:2px auto 12px}",
    ".bc-box h3{margin:0 0 10px;font-size:18px}",
    ".bc-box label{display:block;font-size:11.5px;font-weight:800;color:#5A657C;letter-spacing:.03em;text-transform:uppercase;margin:12px 0 5px}",
    ".bc-box input,.bc-box select,.bc-box textarea{width:100%;box-sizing:border-box;padding:12px;border:1.5px solid #E4E8F2;border-radius:12px;font:inherit;font-size:15px;background:#F6F7FB;color:#0D1424}",
    ".bc-box textarea{min-height:70px}",
    ".bc-big{display:flex;gap:12px;align-items:center;width:100%;text-align:left;background:#F6F7FB;border:1px solid #E4E8F2;border-radius:15px;padding:13px;margin-bottom:8px;font:inherit;cursor:pointer;color:#0D1424}",
    ".bc-big i{font-style:normal;font-size:26px;width:36px;text-align:center}.bc-big b{display:block;font-size:14.5px}.bc-big small{display:block;font-size:12px;color:#5A657C}",
    ".bc-prev{background:#F1F4FA;border-radius:14px;min-height:120px;display:grid;place-items:center;overflow:hidden;margin-bottom:10px}",
    ".bc-prev img{max-width:100%;max-height:48vh;display:block}",
    ".bc-acts{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}",
    ".bc-icons{display:flex;flex-wrap:wrap;gap:6px}.bc-icons button{font-size:22px;width:44px;height:44px;border-radius:12px;border:1.5px solid #E4E8F2;background:#fff;cursor:pointer}.bc-icons button.on{border-color:#1B4DFF;background:#EEF2FF}",
    ".bc-hint{font-size:12px;color:#5A657C;margin-top:6px;line-height:1.5}",
    ".bc-link{word-break:break-all;background:#F6F7FB;border:1px dashed #C9D1E3;border-radius:12px;padding:10px;font-size:13px}",
    ".bc-toast{position:fixed;left:50%;bottom:150px;transform:translate(-50%,20px);opacity:0;background:#0D1424;color:#fff;padding:10px 16px;border-radius:12px;font-size:14px;z-index:2147483600;transition:.25s}.bc-toast.on{opacity:1;transform:translate(-50%,0)}",
    ".bc-exp .bc-row{border-color:#F5D9A8;background:#FFFBF2}",
    ".bc-num{display:flex;align-items:center;gap:8px;margin-top:10px;background:#F6F7FB;border:1px solid #E4E8F2;border-radius:12px;padding:6px 6px 6px 12px}.bc-num span{font-size:12px;color:#5A657C;font-weight:800}.bc-num b{flex:1;font-size:16px;letter-spacing:.04em;font-family:ui-monospace,Menlo,monospace}.bc-num .bc-btn{padding:7px 10px}",
    ".bc-auto{background:#EEF2FF;border-radius:10px;padding:8px 10px;color:#1B3BB3}"
  ].join("\n");
  D.head.appendChild(css);

  var root = D.getElementById("bc");
  if (!root){ root = D.createElement("div"); root.id = "bc"; B.appendChild(root); }
  root.className = "bc";

  /* ------------------------------------------------------------ load */
  function load(){
    return req("GET", "").then(function(d){ S.folders = d.folders; S.docs = d.docs; S.used = d.used; S.limit = d.limit; S.max_file = d.max_file; render(); })
      .catch(function(e){
        if (e.signin){ root.innerHTML = '<h1>My Briefcase</h1><div class="ur">میرا بریف کیس</div><p class="lead">Keep your degrees, experience letters, ID card and passport safe in one place. Get a reminder before they expire.</p><a class="bc-btn blue" style="display:inline-block;text-decoration:none" href="/login?next=/briefcase">Sign in to open your briefcase</a>'; return; }
        root.innerHTML = '<p class="bc-empty">' + esc(e.message) + "</p>";
      });
  }

  function render(){
    if (S.view === "folder") return renderFolder();
    var pct = Math.min(100, Math.round(S.used * 100 / S.limit));
    var exp = S.docs.filter(function(d){ return d.days_left != null && d.days_left <= 60; }).sort(function(a, b){ return a.days_left - b.days_left; });
    var h = '<h1>💼 My Briefcase</h1><div class="ur">میرا بریف کیس — آپ کے تمام اہم کاغذات ایک جگہ</div>'
      + '<p class="lead">Degrees, experience letters, ID card, passport and more. Download them in any format when you need them.</p>'
      + '<div class="bc-lock">🔒<span>Locked (encrypted) on our server. Only you can open your documents, or someone you send a share link to, until it ends.</span></div>'
      + '<div class="bc-use"><i style="width:' + pct + '%"></i></div><div class="bc-usetx">' + mb(S.used) + " of " + mb(S.limit) + " used · " + S.docs.length + " document" + (S.docs.length === 1 ? "" : "s") + "</div>";
    if (exp.length) h += '<div class="bc-sec">⏰ Expiring soon</div><div class="bc-exp">' + exp.map(row).join("") + "</div>";
    h += '<div class="bc-sec">Folders</div><div class="bc-grid">' + S.folders.map(function(f){
      return '<button class="bc-f" data-f="' + esc(f.key) + '"><span class="e">' + esc(f.icon) + "</span><b>" + esc(f.name) + "</b>" + (f.ur ? '<span class="u">' + esc(f.ur) + "</span>" : "") + "<small>" + f.count + " document" + (f.count === 1 ? "" : "s") + "</small></button>";
    }).join("") + '<button class="bc-f new" data-newf="1">＋ New folder</button></div>';
    if (S.docs.length){ h += '<div class="bc-sec">Recently added</div>' + S.docs.slice(0, 5).map(row).join(""); }
    root.innerHTML = h + '<button class="bc-fab" data-add="1">＋ Add document</button>';
    thumbs();
  }

  function row(d){
    return '<div class="bc-row' + (S.pick && S.pick[d.id] ? " on" : "") + '" data-d="' + d.id + '"><span class="ck">✓</span><div class="th" data-th="' + d.id + '">' + kindIcon(d) + '</div><div class="t"><b>' + esc(d.title) + "</b><small>" + esc(d.number ? "No. " + mask(d.number) : folderOf(d.folder).name) + " · " + mb(d.size) + "</small>" + badge(d) + "</div></div>";
  }

  function thumbs(){
    [].forEach.call(root.querySelectorAll("[data-th]"), function(el){
      var d = byId(+el.dataset.th); if (!d || !isImg(d)) return;
      var im = new Image(); im.alt = ""; im.onload = function(){ el.innerHTML = ""; el.appendChild(im); }; im.src = d.url;
    });
  }

  function byId(id){ for (var i = 0; i < S.docs.length; i++) if (S.docs[i].id === id) return S.docs[i]; return null; }

  function renderFolder(){
    var f = folderOf(S.folder), list = S.docs.filter(function(d){ return d.folder === S.folder; });
    var h = '<button class="bc-back" data-home="1">← My Briefcase</button><div class="bc-head"><span style="font-size:30px">' + esc(f.icon) + "</span><h2>" + esc(f.name) + "</h2>"
      + (list.length > 1 ? '<button class="bc-btn ghost" data-sel="1">' + (S.pick ? "Cancel" : "Select") + "</button>" : "")
      + (!f.builtin && f.id ? '<button class="bc-btn ghost" data-fset="' + f.id + '">⋯</button>' : "") + "</div>";
    if (f.ur) h += '<div class="ur" style="margin:-8px 0 10px">' + esc(f.ur) + "</div>";
    h += list.length ? list.map(row).join("") : '<div class="bc-empty">Nothing here yet.<br>Tap <b>Add document</b> to scan or upload one.</div>';
    root.innerHTML = h;
    root.classList.toggle("sel", !!S.pick);
    var old = D.querySelector(".bc-bar"); if (old) old.remove();
    var fab = D.querySelector(".bc-fab"); if (fab) fab.remove();
    if (S.pick){
      var n = Object.keys(S.pick).length, bar = D.createElement("div"); bar.className = "bc-bar";
      bar.innerHTML = '<button class="bc-btn blue" data-comb="1"' + (n ? "" : " disabled") + ">📄 One PDF (" + n + ")</button><button class=\"bc-btn red\" data-delsel=\"1\"" + (n ? "" : " disabled") + ">Delete</button>";
      B.appendChild(bar);
    } else {
      root.insertAdjacentHTML("beforeend", '<button class="bc-fab" data-add="1">＋ Add document</button>');
    }
    thumbs();
  }

  function go(view, folder){
    S.view = view; S.folder = folder || null; S.pick = null;
    var bar = D.querySelector(".bc-bar"); if (bar) bar.remove();
    root.classList.remove("sel");
    render(); window.scrollTo(0, 0);
    try { history.replaceState(null, "", view === "folder" ? "#f-" + folder : location.pathname); } catch (e) {}
  }

  /* ------------------------------------------------------------ sheets */
  function sheet(html){
    var ov = D.createElement("div"); ov.className = "bc-sh"; ov.innerHTML = '<div class="bc-box"><div class="bc-grab"></div>' + html + "</div>";
    ov.addEventListener("click", function(e){ if (e.target === ov || e.target.closest("[data-x]")) ov.remove(); });
    B.appendChild(ov); return ov;
  }
  function folderSelect(sel){
    return '<select name="folder">' + S.folders.map(function(f){ return '<option value="' + esc(f.key) + '"' + (f.key === sel ? " selected" : "") + ">" + esc(f.icon + " " + f.name) + "</option>"; }).join("") + "</select>";
  }

  function addMenu(){
    var ov = sheet('<h3>Add a document</h3>'
      + '<button class="bc-big" data-a="scan"><i>📷</i><span><b>Scan with camera</b><small>Paper, certificate, letter - straightened and cleaned (XpertScan)</small></span></button>'
      + '<button class="bc-big" data-a="id"><i>🪪</i><span><b>Scan an ID card / licence</b><small>Front and back on one page - number and expiry are read for you</small></span></button>'
      + '<button class="bc-big" data-a="pp"><i>🛂</i><span><b>Scan a passport</b><small>The photo page - number and expiry are read for you</small></span></button>'
      + '<button class="bc-big" data-a="up"><i>⬆️</i><span><b>Upload a file</b><small>PDF, picture, Word or Excel - up to 8 MB each</small></span></button>'
      + '<button class="bc-btn ghost" data-x="1" style="width:100%;margin-top:4px">Cancel</button>');
    ov.addEventListener("click", function(e){
      var b = e.target.closest("[data-a]"); if (!b) return; var a = b.dataset.a; ov.remove();
      if (a === "up") return pickFiles();
      if (!window.XSCAN){ toast("The scanner is loading, try again in a moment."); return; }
      var card = a === "id" || a === "pp", folder = card ? "id" : (S.view === "folder" ? S.folder : "other");
      XSCAN.open({start: a === "id" ? "id" : "", sendLabel: "Save to My Briefcase", sendIcon: "💼", sendSub: "Locked, only you can open it", onSend: function(file, info){
        return new Promise(function(res){ setTimeout(function(){ details([file], folder, card ? (a === "pp" ? "pp" : "id") : "", info); res(); }, 50); });
      }});
    });
  }

  function pickFiles(){
    var inp = D.createElement("input"); inp.type = "file"; inp.multiple = true; inp.style.display = "none";
    inp.accept = "application/pdf,image/jpeg,image/png,image/webp,.doc,.docx,.xls,.xlsx,.ppt,.pptx";
    B.appendChild(inp);
    inp.addEventListener("change", function(){ var fs = [].slice.call(inp.files); inp.remove(); if (fs.length) details(fs, S.view === "folder" ? S.folder : "other", false); });
    inp.click();
  }

  function details(files, folder, isId, info){
    var one = files.length === 1, f0 = files[0];
    var big = files.filter(function(f){ return f.size > S.max_file; });
    var ov = sheet("<h3>" + (one ? "Save to My Briefcase" : "Save " + files.length + " files") + "</h3>"
      + (big.length ? '<p class="bc-hint" style="color:#B91C1C">' + big.length + " file" + (big.length === 1 ? " is" : "s are") + " over 8 MB and will be skipped.</p>" : "")
      + (one ? '<label>Name</label><input name="title" maxlength="120" placeholder="' + (isId ? "e.g. My CNIC, Passport" : "e.g. Matric certificate, Experience letter") + '" value="' + esc(/^XpertScan-/.test(f0.name) ? "" : f0.name.replace(/\.[^.]+$/, "")) + '">' : "")
      + "<label>Folder</label>" + folderSelect(folder)
      + (one ? '<label>Card / passport number (optional)</label><input name="number" maxlength="40" autocomplete="off" placeholder="e.g. 35202-1234567-1">' : "")
      + "<label>Expiry date (optional)</label><input name=\"expires\" type=\"date\">"
      + '<p class="bc-hint bc-auto" style="display:none"></p>'
      + '<p class="bc-hint">For an ID card, passport, licence or visa. You get a reminder 60, 30 and 7 days before, and on the day.<br><span dir="rtl">میعاد ختم ہونے سے پہلے آپ کو یاددہانی ملے گی۔</span></p>'
      + (one ? '<label>Note (optional)</label><textarea name="note" maxlength="300" placeholder="e.g. Original is in the blue file at home"></textarea>' : "")
      + '<div class="bc-acts"><button class="bc-btn ghost" data-x="1">Cancel</button><button class="bc-btn blue" data-save="1">Save</button></div><p class="bc-hint bc-st"></p>');
    if (isId && info && info.pages && info.pages.length && window.XSCAN && XSCAN.read) autoRead(ov, info.pages, isId);
    ov.querySelector("[data-save]").addEventListener("click", function(){
      var btn = this, st = ov.querySelector(".bc-st"), ok = files.filter(function(f){ return f.size <= S.max_file; });
      if (!ok.length) return;
      btn.disabled = true;
      var val = function(n){ var e = ov.querySelector("[name=" + n + "]"); return e ? e.value : ""; };
      var i = 0, done = 0, errs = [];
      (function next(){
        if (i >= ok.length){
          ov.remove();
          toast(done ? "Saved ✓" + (done > 1 ? " (" + done + ")" : "") : "Not saved");
          if (errs.length) alertBox(errs.join("\n"));
          var fk = val("folder"); load().then(function(){ if (done) go("folder", fk); });
          return;
        }
        var f = ok[i++], fd = new FormData();
        fd.append("file", f, f.name); fd.append("folder", val("folder")); fd.append("expires", val("expires"));
        if (one){ fd.append("title", val("title")); fd.append("note", val("note")); fd.append("number", val("number")); }
        st.textContent = "Saving " + i + " of " + ok.length + "…";
        req("POST", "docs/", fd).then(function(){ done++; setTimeout(next, 1100); }).catch(function(e){ errs.push(f.name + ": " + e.message); if (e.signin) location.href = "/login?next=/briefcase"; setTimeout(next, 1100); });
      })();
    });
  }

  function alertBox(t){ sheet("<h3>Some files were not saved</h3><p style=\"white-space:pre-line;font-size:14px\">" + esc(t) + '</p><button class="bc-btn" data-x="1" style="width:100%">OK</button>'); }

  function mask(n){ n = String(n || ""); var k = n.replace(/[^A-Za-z0-9]/g, ""); if (k.length <= 4) return n; var keep = 0; return n.replace(/[A-Za-z0-9]/g, function(c){ keep++; return keep <= 2 || keep > k.length - 2 ? c : "•"; }); }

  /* Reads the number and the expiry date from the text of an ID card, driving licence or passport.
     Passport: the two machine lines at the bottom (with check digits). CNIC: 12345-1234567-1 and the latest date. */
  var MON = {JAN: 1, FEB: 2, MAR: 3, APR: 4, MAY: 5, JUN: 6, JUL: 7, AUG: 8, SEP: 9, OCT: 10, NOV: 11, DEC: 12};
  function iso(y, m, d){ if (y < 100) y += 2000; if (m < 1 || m > 12 || d < 1 || d > 31 || y < 1950 || y > 2100) return null; return y + "-" + ("0" + m).slice(-2) + "-" + ("0" + d).slice(-2); }
  function mrzCheck(s, digit){ var w = [7, 3, 1], t = 0; for (var i = 0; i < s.length; i++){ var c = s.charAt(i), v = c === "<" ? 0 : /\d/.test(c) ? +c : c.charCodeAt(0) - 55; t += v * w[i % 3]; } return t % 10 === +digit; }
  function fix(t, bad, good){   // a letter OCR put next to a digit is usually a digit (O->0, I/L->1); done twice for runs
    var cls = "[" + bad.replace(/[|]/g, "\\|") + "]", re = new RegExp("(\\d)" + cls + "|" + cls + "(\\d)", "g");
    for (var k = 0; k < 2; k++) t = t.replace(re, function(m, a, b){ return a != null ? a + good : good + b; });
    return t;
  }
  function cardInfo(text){
    var out = {kind: "", number: "", expires: "", sure: false};
    var T = String(text || "").replace(/\r/g, ""), U = T.toUpperCase();
    // passport: line 2 of the machine zone
    var lines = U.split("\n").map(function(l){ return l.replace(/\s+/g, "").replace(/[«‹]/g, "<"); });
    for (var i = 0; i < lines.length; i++){
      var l = fix(lines[i], "O", "0");
      var m = l.match(/([A-Z0-9<]{9})(\d)([A-Z<]{3})(\d{6})(\d)([MF<X])(\d{6})(\d)/);
      if (m && (mrzCheck(m[1], m[2]) || mrzCheck(m[7], m[8]))){
        out.kind = "pp"; out.number = m[1].replace(/<+$/g, "").replace(/</g, "");
        var e = m[7]; out.expires = iso(+e.slice(0, 2), +e.slice(2, 4), +e.slice(4, 6)) || ""; out.sure = mrzCheck(m[7], m[8]); return out;
      }
    }
    if (/PASSPORT/.test(U)) out.kind = "pp";
    else if (/LICEN[CS]E|DRIVING/.test(U)) out.kind = "dl";
    else if (/IDENTITY|NADRA|PAKISTAN|CNIC|NATIONAL/.test(U)) out.kind = "id";
    // Pakistani CNIC number (OCR sometimes reads O for 0 and spaces around the dashes)
    var D2 = fix(fix(U, "O", "0"), "IL|", "1");
    var c = D2.match(/(\d{5})\s*[-–—~]\s*(\d{7})\s*[-–—~]\s*(\d)(?!\d)/) || D2.match(/(?:^|\D)(\d{5})(\d{7})(\d)(?!\d)/);
    if (c){ out.number = c[1] + "-" + c[2] + "-" + c[3]; if (!out.kind) out.kind = "id"; }
    // dates: 12.05.2030, 12/05/2030, 12-05-2030, 12 MAY 2030
    var dates = [], re = /(\d{1,2})\s*[.,\/\-]\s*(\d{1,2})\s*[.,\/\-]\s*(\d{4})|(\d{1,2})\s*(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*[\s\/]*(\d{2,4})/g, x;
    while ((x = re.exec(D2))){
      var dt = x[3] ? iso(+x[3], +x[2], +x[1]) : iso(+x[6], MON[x[5]], +x[4]);
      if (dt) dates.push({d: dt, at: x.index});
    }
    var kw = D2.search(/EXPIR|VALID\s*(UP\s*TO|TILL|UNTIL)|DATE\s*OF\s*EXP/);
    if (kw >= 0){ var after = dates.filter(function(z){ return z.at >= kw; }); if (after.length){ out.expires = after[0].d; out.sure = true; } }
    if (!out.expires && dates.length){ out.expires = dates.map(function(z){ return z.d; }).sort().pop(); }
    if (/LIFE\s*TIME/.test(D2) && !out.sure){ out.expires = ""; out.life = true; }
    if (!out.number && out.kind === "pp"){ var pn = D2.match(/\b([A-Z]{1,2}\d{6,8})\b/); if (pn) out.number = pn[1]; }
    return out;
  }

  function autoRead(ov, pages, kind){
    var tip = ov.querySelector(".bc-auto"), set = function(n, v){ var e = ov.querySelector("[name=" + n + "]"); if (e && v && !e.value) e.value = v; };
    tip.style.display = "block"; tip.textContent = "⏳ Reading the number and expiry date from your card…";
    XSCAN.read(pages.slice(0, 2), "eng", function(st, p){ if (st === "recognizing text") tip.textContent = "⏳ Reading the card… " + Math.round(p * 100) + "%"; })
      .then(function(t){
        if (!ov.isConnected) return;
        var r = cardInfo(t);
        set("number", r.number); set("expires", r.expires);
        set("title", r.kind === "pp" ? "Passport" : r.kind === "dl" ? "Driving licence" : r.kind === "id" || kind === "id" ? "CNIC (ID card)" : "");
        if (!r.number && !r.expires) tip.textContent = "Could not read the number or date. Please type them (a clearer, flat photo in good light helps).";
        else tip.innerHTML = "✅ Found " + [r.number ? "the number" : "", r.expires ? "the expiry date" : ""].filter(Boolean).join(" and ") + ". <b>Please check them</b> before saving." + (r.life ? " This card looks like it has no expiry (lifetime)." : "") + (!r.expires && !r.life ? " Add the expiry date yourself." : "");
      })
      .catch(function(){ if (ov.isConnected) tip.textContent = "Could not read the card here. Please type the number and expiry date."; });
  }

  /* ------------------------------------------------------------ one document */
  function openDoc(d){
    var ov = sheet('<div class="bc-prev">' + (isImg(d) ? '<img alt="" src="' + d.url + '">' : '<div style="font-size:60px;padding:20px">' + kindIcon(d) + "</div>") + "</div>"
      + "<h3 style=\"margin-bottom:2px\">" + esc(d.title) + '</h3><div style="font-size:12.5px;color:#5A657C">' + esc(folderOf(d.folder).icon + " " + folderOf(d.folder).name) + " · " + mb(d.size) + " · added " + nice(d.created.slice(0, 10)) + "</div>" + badge(d)
      + (d.number ? '<div class="bc-num"><span>No.</span><b data-num="1">' + esc(mask(d.number)) + '</b><button class="bc-btn ghost" data-o="eye">👁️</button><button class="bc-btn ghost" data-o="cpn">📋</button></div>' : "")
      + (d.note ? '<p style="font-size:14px;margin:8px 0 0">' + esc(d.note) + "</p>" : "")
      + '<div class="bc-sec">Download</div><div class="bc-acts">'
      + '<button class="bc-btn ghost" data-o="orig">⬇️ Original</button>'
      + (isImg(d) ? '<button class="bc-btn ghost" data-o="pdf">📄 As PDF</button><button class="bc-btn ghost" data-o="jpg">🖼️ As JPG</button><button class="bc-btn ghost" data-o="png">🖼️ As PNG</button>' : "")
      + (isPdf(d) ? '<button class="bc-btn ghost" data-o="view">👁️ Open</button>' : "") + "</div>"
      + '<div class="bc-sec">Send</div><div class="bc-acts">'
      + '<button class="bc-btn blue" data-o="link">🔗 Share a link</button>'
      + (navigator.share ? '<button class="bc-btn ghost" data-o="share">📤 Share the file</button>' : "") + "</div>"
      + '<p class="bc-hint">Share a link for a job application, a bank or an office. It stops working by itself.</p>'
      + '<div class="bc-sec">Manage</div><div class="bc-acts"><button class="bc-btn ghost" data-o="edit">✏️ Edit / expiry</button><button class="bc-btn red" data-o="del">🗑️ Delete</button></div>'
      + '<button class="bc-btn ghost" data-x="1" style="width:100%;margin-top:12px">Close</button>');
    ov.addEventListener("click", function(e){
      var b = e.target.closest("[data-o]"); if (!b) return; var o = b.dataset.o;
      if (o === "orig") dl(d.url + "?dl=1", d.fname);
      if (o === "eye"){ var nb = ov.querySelector("[data-num]"); nb.textContent = nb.textContent === d.number ? mask(d.number) : d.number; }
      if (o === "cpn") (navigator.clipboard ? navigator.clipboard.writeText(d.number) : Promise.reject()).then(function(){ toast("Number copied"); }).catch(function(){ toast(d.number); });
      if (o === "view") window.open(d.url, "_blank");
      if (o === "pdf" || o === "jpg" || o === "png") convert(d, o, b);
      if (o === "share") shareFile(d, b);
      if (o === "link"){ ov.remove(); shareLink(d); }
      if (o === "edit"){ ov.remove(); edit(d); }
      if (o === "del"){ ov.remove(); confirmDel([d.id]); }
    });
  }

  function dl(url, name){ var a = D.createElement("a"); a.href = url; a.download = name || ""; B.appendChild(a); a.click(); a.remove(); }
  function base(d){ return (d.title || "document").replace(/[^\w\- ]+/g, "").trim().replace(/\s+/g, "-").slice(0, 60) || "document"; }
  function getBlob(d){ return fetch(d.url, {credentials: "same-origin"}).then(function(r){ if (!r.ok) throw new Error("Could not open it."); return r.blob(); }); }
  function canvasOf(d){
    return getBlob(d).then(function(bl){ return new Promise(function(res, rej){
      var u = URL.createObjectURL(bl), im = new Image();
      im.onload = function(){ var c = D.createElement("canvas"); c.width = im.naturalWidth; c.height = im.naturalHeight; var g = c.getContext("2d"); g.fillStyle = "#fff"; g.fillRect(0, 0, c.width, c.height); g.drawImage(im, 0, 0); URL.revokeObjectURL(u); res(c); };
      im.onerror = function(){ URL.revokeObjectURL(u); rej(new Error("Could not read the picture.")); };
      im.src = u;
    }); });
  }
  function fit(c, max){
    var k = Math.min(1, max / Math.max(c.width, c.height)); if (k === 1) return c;
    var o = D.createElement("canvas"); o.width = Math.round(c.width * k); o.height = Math.round(c.height * k); o.getContext("2d").drawImage(c, 0, 0, o.width, o.height); return o;
  }
  function convert(d, kind, btn){
    btn.disabled = true;
    canvasOf(d).then(function(c){
      if (kind === "pdf"){ var cc = fit(c, 2000); var blob = pdf([{url: cc.toDataURL("image/jpeg", 0.88), w: cc.width, h: cc.height}]); dlBlob(blob, base(d) + ".pdf"); }
      else c.toBlob(function(b){ dlBlob(b, base(d) + "." + kind); }, kind === "png" ? "image/png" : "image/jpeg", 0.92);
    }).catch(function(e){ toast(e.message); }).then(function(){ btn.disabled = false; });
  }
  function dlBlob(b, name){ var u = URL.createObjectURL(b); dl(u, name); setTimeout(function(){ URL.revokeObjectURL(u); }, 4000); }

  /* A small PDF writer: each picture becomes one A4 page (portrait or landscape to suit it). */
  function pdf(pages){
    var parts = [], offs = [], len = 0, n = 0;
    function add(s){ if (typeof s === "string"){ var u = new Uint8Array(s.length); for (var i = 0; i < s.length; i++) u[i] = s.charCodeAt(i) & 255; s = u; } parts.push(s); len += s.length; }
    function obj(body, bin){ n++; offs[n] = len; add(n + " 0 obj\n"); add(body); if (bin){ add(bin); add("\nendstream"); } add("\nendobj\n"); return n; }
    add("%PDF-1.4\n%\xE2\xE3\xCF\xD3\n");
    var kids = [], pagesId = pages.length * 3 + 2;
    obj("<< /Type /Catalog /Pages " + pagesId + " 0 R >>");
    pages.forEach(function(p, i){
      var raw = atob(p.url.split(",")[1]), bin = new Uint8Array(raw.length); for (var j = 0; j < raw.length; j++) bin[j] = raw.charCodeAt(j);
      var land = p.w > p.h, W = land ? 842 : 595, H = land ? 595 : 842, m = 24, k = Math.min((W - 2 * m) / p.w, (H - 2 * m) / p.h), w = p.w * k, h = p.h * k, x = (W - w) / 2, y = (H - h) / 2;
      var img = obj("<< /Type /XObject /Subtype /Image /Width " + p.w + " /Height " + p.h + " /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length " + bin.length + " >>\nstream\n", bin);
      var cs = "q " + w.toFixed(2) + " 0 0 " + h.toFixed(2) + " " + x.toFixed(2) + " " + y.toFixed(2) + " cm /Im" + i + " Do Q";
      var con = obj("<< /Length " + cs.length + " >>\nstream\n", cs);
      kids.push(obj("<< /Type /Page /Parent " + pagesId + " 0 R /MediaBox [0 0 " + W + " " + H + "] /Resources << /XObject << /Im" + i + " " + img + " 0 R >> >> /Contents " + con + " 0 R >>"));
    });
    obj("<< /Type /Pages /Kids [" + kids.map(function(k){ return k + " 0 R"; }).join(" ") + "] /Count " + kids.length + " >>");
    var xref = len, s = "xref\n0 " + (n + 1) + "\n0000000000 65535 f \n";
    for (var i = 1; i <= n; i++) s += ("0000000000" + offs[i]).slice(-10) + " 00000 n \n";
    add(s + "trailer\n<< /Size " + (n + 1) + " /Root 1 0 R >>\nstartxref\n" + xref + "\n%%EOF");
    return new Blob(parts, {type: "application/pdf"});
  }

  function combine(ids){
    var docs = ids.map(byId).filter(Boolean), imgs = docs.filter(isImg), skip = docs.length - imgs.length;
    if (!imgs.length){ toast("Only pictures can be joined into one PDF. PDF files download as they are."); return; }
    toast("Making the PDF…");
    var pages = [], i = 0;
    (function next(){
      if (i >= imgs.length){ dlBlob(pdf(pages), "My-documents-" + new Date().toISOString().slice(0, 10) + ".pdf"); if (skip) toast(skip + " PDF/Office file" + (skip === 1 ? " was" : "s were") + " left out - download " + (skip === 1 ? "it" : "them") + " on its own."); go("folder", S.folder); return; }
      canvasOf(imgs[i++]).then(function(c){ var cc = fit(c, 1800); pages.push({url: cc.toDataURL("image/jpeg", 0.85), w: cc.width, h: cc.height}); next(); }).catch(function(e){ toast(e.message); });
    })();
  }

  function shareFile(d, btn){
    btn.disabled = true;
    getBlob(d).then(function(bl){
      var f = new File([bl], d.fname, {type: d.mime});
      if (navigator.canShare && !navigator.canShare({files: [f]})) throw new Error("Your phone cannot share this file. Use Share a link.");
      return navigator.share({files: [f], title: d.title});
    }).catch(function(e){ if (e && e.name !== "AbortError") toast(e.message || "Could not share it."); }).then(function(){ btn.disabled = false; });
  }

  function shareLink(d){
    var ov = sheet("<h3>🔗 Share a link</h3><p style=\"font-size:14px;margin:0 0 6px\">Anyone with the link can open <b>" + esc(d.title) + "</b> until it ends. Then it stops working by itself.</p>"
      + "<label>Link works for</label><select name=\"h\"><option value=\"1\">1 hour</option><option value=\"24\" selected>24 hours</option><option value=\"72\">3 days</option><option value=\"168\">7 days</option></select>"
      + '<div class="bc-acts"><button class="bc-btn ghost" data-x="1">Cancel</button><button class="bc-btn blue" data-mk="1">Make link</button></div><div class="bc-out"></div>'
      + '<button class="bc-btn red" data-stop="1" style="width:100%;margin-top:10px">Stop all links to this document</button>');
    ov.querySelector("[data-mk]").addEventListener("click", function(){
      var b = this; b.disabled = true;
      req("POST", "docs/" + d.id + "/share/", {hours: +ov.querySelector("[name=h]").value}).then(function(r){
        var url = location.origin + r.url, until = new Date(r.expires_at), msg = d.title + " — " + url;
        ov.querySelector(".bc-out").innerHTML = '<label>Your link (ends ' + esc(until.toLocaleString()) + ')</label><div class="bc-link">' + esc(url) + '</div><div class="bc-acts"><button class="bc-btn" data-cp="1">📋 Copy</button><a class="bc-btn blue" style="text-align:center;text-decoration:none;background:#16a34a" target="_blank" rel="noopener" href="https://wa.me/?text=' + encodeURIComponent(msg) + '">WhatsApp</a></div>';
        ov.querySelector("[data-cp]").addEventListener("click", function(){ (navigator.clipboard ? navigator.clipboard.writeText(url) : Promise.reject()).then(function(){ toast("Link copied"); }).catch(function(){ toast(url); }); });
      }).catch(function(e){ toast(e.message); b.disabled = false; });
    });
    ov.querySelector("[data-stop]").addEventListener("click", function(){
      req("DELETE", "docs/" + d.id + "/share/").then(function(r){ toast(r.stopped ? "Links stopped" : "No links were open"); ov.remove(); }).catch(function(e){ toast(e.message); });
    });
  }

  function edit(d){
    var ov = sheet("<h3>Edit</h3><label>Name</label><input name=\"title\" maxlength=\"120\" value=\"" + esc(d.title) + "\"><label>Folder</label>" + folderSelect(d.folder)
      + "<label>Card / passport number</label><input name=\"number\" maxlength=\"40\" autocomplete=\"off\" value=\"" + esc(d.number || "") + "\">"
      + "<label>Expiry date</label><input name=\"expires\" type=\"date\" value=\"" + esc(d.expires || "") + "\"><p class=\"bc-hint\">Leave empty if it does not expire.</p>"
      + "<label>Note</label><textarea name=\"note\" maxlength=\"300\">" + esc(d.note) + "</textarea>"
      + '<div class="bc-acts"><button class="bc-btn ghost" data-x="1">Cancel</button><button class="bc-btn blue" data-ok="1">Save</button></div>');
    ov.querySelector("[data-ok]").addEventListener("click", function(){
      var b = this, v = function(n){ return ov.querySelector("[name=" + n + "]").value; }; b.disabled = true;
      req("PATCH", "docs/" + d.id + "/", {title: v("title"), folder: v("folder"), expires: v("expires"), note: v("note"), number: v("number")})
        .then(function(){ ov.remove(); toast("Saved ✓"); return load(); }).catch(function(e){ toast(e.message); b.disabled = false; });
    });
  }

  function confirmDel(ids){
    var ov = sheet("<h3>Delete " + (ids.length === 1 ? "this document" : ids.length + " documents") + "?</h3><p style=\"font-size:14px\">It is removed from our server for good and any share links stop working.</p>"
      + '<div class="bc-acts"><button class="bc-btn ghost" data-x="1">Keep</button><button class="bc-btn red" data-yes="1">Delete</button></div>');
    ov.querySelector("[data-yes]").addEventListener("click", function(){
      this.disabled = true;
      var p = Promise.resolve();
      ids.forEach(function(id){ p = p.then(function(){ return req("DELETE", "docs/" + id + "/"); }); });
      p.then(function(){ toast("Deleted"); }).catch(function(e){ toast(e.message); }).then(function(){ ov.remove(); S.pick = null; load(); });
    });
  }

  function newFolder(f){
    var icon = f ? f.icon : ICONS[0];
    var ov = sheet("<h3>" + (f ? "Folder" : "New folder") + "</h3><label>Name</label><input name=\"n\" maxlength=\"40\" placeholder=\"e.g. Car papers, Children, Bank\" value=\"" + esc(f ? f.name : "") + "\"><label>Icon</label><div class=\"bc-icons\">"
      + ICONS.map(function(i){ return '<button type="button" data-ic="' + i + '"' + (i === icon ? ' class="on"' : "") + ">" + i + "</button>"; }).join("") + "</div>"
      + '<div class="bc-acts"><button class="bc-btn ghost" data-x="1">Cancel</button><button class="bc-btn blue" data-ok="1">Save</button></div>'
      + (f ? '<button class="bc-btn red" data-rm="1" style="width:100%;margin-top:10px">Delete folder (documents move to Other)</button>' : ""));
    ov.querySelector(".bc-icons").addEventListener("click", function(e){ var b = e.target.closest("[data-ic]"); if (!b) return; icon = b.dataset.ic; [].forEach.call(ov.querySelectorAll("[data-ic]"), function(x){ x.classList.toggle("on", x === b); }); });
    ov.querySelector("[data-ok]").addEventListener("click", function(){
      var b = this, name = ov.querySelector("[name=n]").value; b.disabled = true;
      (f ? req("PATCH", "folders/" + f.id + "/", {name: name, icon: icon}) : req("POST", "folders/", {name: name, icon: icon}))
        .then(function(r){ ov.remove(); return load().then(function(){ if (!f) go("folder", r.key); }); }).catch(function(e){ toast(e.message); b.disabled = false; });
    });
    var rm = ov.querySelector("[data-rm]");
    if (rm) rm.addEventListener("click", function(){ req("DELETE", "folders/" + f.id + "/").then(function(){ ov.remove(); S.view = "home"; load(); }).catch(function(e){ toast(e.message); }); });
  }

  /* ------------------------------------------------------------ clicks */
  B.addEventListener("click", function(e){
    var t = e.target;
    if (t.closest(".bc-sh")) return;
    if (t.closest("[data-add]")) return addMenu();
    if (t.closest("[data-newf]")) return newFolder();
    if (t.closest("[data-home]")) return go("home");
    var fs = t.closest("[data-fset]"); if (fs) return newFolder(folderOf("f" + fs.dataset.fset));
    if (t.closest("[data-sel]")){ S.pick = S.pick ? null : {}; return renderFolder(); }
    if (t.closest("[data-comb]")) return combine(Object.keys(S.pick || {}).map(Number));
    if (t.closest("[data-delsel]")) return confirmDel(Object.keys(S.pick || {}).map(Number));
    var f = t.closest("[data-f]"); if (f) return go("folder", f.dataset.f);
    var r = t.closest("[data-d]");
    if (r){
      var id = +r.dataset.d;
      if (S.pick){ if (S.pick[id]) delete S.pick[id]; else S.pick[id] = 1; return renderFolder(); }
      var d = byId(id); if (d) openDoc(d);
    }
  });

  load().then(function(){
    var h = location.hash, m;
    if ((m = h.match(/^#d(\d+)$/))){ var d = byId(+m[1]); if (d) openDoc(d); }
    else if ((m = h.match(/^#f-(\w+)$/)) && S.folders.some(function(f){ return f.key === m[1]; })) go("folder", m[1]);
    else if (h === "#add") addMenu();
  });
  window.XBRIEF = {_pdf: pdf, _card: cardInfo, reload: load};
})();
