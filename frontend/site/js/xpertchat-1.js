/* XpertChat: app bar, bottom tabs, search, two panes on computers, QR codes (my code, scan, group invite) and
   personal stickers. Works on chat.html, groups.html, group.html and nearby.html. */
(function(){
  "use strict";
  if (window.XCXC) return; window.XCXC = 1;
  var D = document, B = D.body, P = location.pathname.replace(/\/+$/, "") || "/";
  var page = D.getElementById("threadbox") ? "chat" : (D.getElementById("gv") ? "group" : (/\/nearby/.test(P) ? "nearby" : (/\/groups/.test(P) ? "groups" : "")));
  if (!page) return;
  function $(i){ return D.getElementById(i); }
  function esc(s){ return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function ck(n){ var x = D.cookie.match("(^|;)\\s*" + n + "\\s*=\\s*([^;]+)"); return x ? x.pop() : ""; }
  var ICON = {
    search: '<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>',
    qr: '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><path d="M14 14h3v3h-3zM20 14v.01M14 20h.01M17 17h4v4"/></svg>',
    more: '<svg viewBox="0 0 24 24"><circle cx="12" cy="5" r="1.4" fill="currentColor"/><circle cx="12" cy="12" r="1.4" fill="currentColor"/><circle cx="12" cy="19" r="1.4" fill="currentColor"/></svg>',
    chats: '<svg viewBox="0 0 24 24"><path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/></svg>',
    groups: '<svg viewBox="0 0 24 24"><circle cx="9" cy="8" r="3.2"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><circle cx="17" cy="9" r="2.5"/><path d="M15.5 14.2A5 5 0 0 1 21 19"/></svg>',
    nearby: '<svg viewBox="0 0 24 24"><path d="M5 12.5a10 10 0 0 1 14 0M8 15.5a6 6 0 0 1 8 0"/><circle cx="12" cy="19" r="1.3" fill="currentColor"/><path d="M2 9.5a14.5 14.5 0 0 1 20 0"/></svg>',
    plus: '<svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>',
    home: '<svg viewBox="0 0 24 24"><path d="M3 10.5L12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/></svg>'
  };
  B.classList.add("xc-app", "xc-" + page + "page");
  if (page === "nearby") B.classList.add("xc-nearby");

  // ---------- app bar ----------
  var bar = D.createElement("div"); bar.className = "xcbar";
  bar.innerHTML = '<img src="/brand/xpertchat/mark-64.png" alt="" onerror="this.style.display=\'none\'"><b>Xpert<i>Chat</i></b>'
    + (page === "chat" ? '<button type="button" data-xc="search" aria-label="Search">' + ICON.search + '</button>' : '')
    + '<button type="button" data-xc="qr" aria-label="QR code">' + ICON.qr + '</button><button type="button" data-xc="menu" aria-label="Menu">' + ICON.more + '</button>';
  var srch = D.createElement("div"); srch.className = "xcsrch"; srch.innerHTML = '<input type="search" placeholder="Search chats" aria-label="Search chats">';

  // ---------- bottom tabs (phones) ----------
  var tabs = D.createElement("nav"); tabs.className = "xctabs";
  tabs.innerHTML = [["chat", "/chat", "Chats", ICON.chats], ["groups", "/groups", "Groups", ICON.groups], ["nearby", "/nearby", "Offline", ICON.nearby], ["qr", "#xcqr", "QR code", ICON.qr], ["home", "/", "Home", ICON.home]]
    .map(function(t){ return '<a href="' + t[1] + '"' + (t[0] === "qr" ? ' data-xc="qr"' : '') + ' class="' + (t[0] === page || (t[0] === "groups" && page === "group") ? "on" : "") + '">' + t[3] + '<span>' + t[2] + '</span></a>'; }).join("");
  B.appendChild(tabs);

  function listMode(on){ B.classList.toggle("xc-list", !!on); }

  if (page === "chat"){
    // two panes: left = chats, right = the open conversation
    var wrap = D.querySelector(".wrap"), h1 = wrap && wrap.querySelector(":scope > h1"), tb = $("threadbox");
    if (wrap && h1 && tb){
      var left = D.createElement("div"), pane = D.createElement("div"), empty = D.createElement("div");
      left.className = "xcleft"; pane.className = "xcpane"; empty.className = "xcempty";
      empty.innerHTML = '<img src="/brand/xpertchat/mark-256.webp" alt=""><b>XpertChat</b><p>Pick a chat on the left, or start a new one.<br>Messages, photos, voice notes and files, on phone and computer.</p>';
      [].slice.call(wrap.children).forEach(function(c){ if (c !== h1 && c !== tb) left.appendChild(c); });
      left.insertBefore(srch, left.firstChild); left.insertBefore(bar, left.firstChild);
      pane.appendChild(h1); pane.appendChild(tb); pane.appendChild(empty);
      wrap.appendChild(left); wrap.appendChild(pane);
      var msgs = $("msgs3"); if (msgs) msgs.classList.add("xcwall");
    }
    var fab = D.createElement("button"); fab.className = "xcfab"; fab.type = "button"; fab.setAttribute("aria-label", "New chat"); fab.innerHTML = ICON.plus;
    fab.onclick = function(){ var n = $("newchat3"); if (n) n.click(); window.scrollTo(0, 0); };
    B.appendChild(fab);
    var sync = function(){ listMode(!B.classList.contains("inchat")); var cur = window.XC3 && XC3.cur && XC3.cur();
      [].forEach.call(D.querySelectorAll(".trow2"), function(r){ r.classList.toggle("xc-cur", !!(cur && String(cur.id) === r.getAttribute("data-open3"))); }); };
    new MutationObserver(sync).observe(B, {attributes: true, attributeFilter: ["class"]}); sync();
    // search the chat list
    var q = srch.querySelector("input"), filt = function(){ var t = q.value.trim().toLowerCase();
      [].forEach.call(D.querySelectorAll("#list5 .trow2"), function(r){ r.style.display = !t || r.textContent.toLowerCase().indexOf(t) > -1 ? "" : "none"; }); };
    q.addEventListener("input", filt);
    var l5 = $("list5"); if (l5) new MutationObserver(function(){ filt(); sync(); }).observe(l5, {childList: true});
    // open a chat straight from a link: /chat?open=<id>
    var op = new URLSearchParams(location.search).get("open");
    if (op && /^\d+$/.test(op)) setTimeout(function(){ var r = D.querySelector('[data-open3="' + op + '"]'); if (r) r.click(); }, 900);
  } else {
    var host = page === "nearby" ? $("app") : D.querySelector(".wrap");
    if (host) host.parentNode.insertBefore(bar, host);
    var markList = function(){ var inConv = page === "group" || !!D.querySelector(".chat .msgs, #msgs"); listMode(!inConv); bar.style.display = inConv ? "none" : ""; };
    new MutationObserver(markList).observe(B, {childList: true, subtree: true}); markList();
    if (page === "nearby") new MutationObserver(function(){ var m = $("msgs"); if (m && !m.classList.contains("xcwall")) m.classList.add("xcwall"); }).observe(B, {childList: true, subtree: true});
    if (page === "group") new MutationObserver(function(){ var g = $("glog"); if (g && !g.classList.contains("xcwall")) g.classList.add("xcwall"); groupQR(); }).observe(B, {childList: true, subtree: true});
  }

  // ---------- menu ----------
  function menu(){
    var old = D.querySelector(".xcmenu"); if (old){ old.remove(); return; }
    var m = D.createElement("div"); m.className = "xcmenu";
    var items = [["/chat", "💬 Chats"], ["/groups", "👥 Groups and channels"], ["/chat-rooms", "🗨️ Chat rooms"], ["/nearby", "📡 Offline chat (no internet)"], ["#xcqr", "▦ My QR code / scan"]];
    if (page === "chat") items.splice(0, 1, ["#new", "➕ New chat"], ["#group", "👥 New group"], ["#sel", "☑️ Select chats"], ["#priv", "🔒 Groups privacy"], ["/groups", "🔎 Find groups"]);
    items.push(["/safety", "🛡️ Privacy and safety"], ["/", "🏠 XpertCreation home"]);
    m.innerHTML = items.map(function(i){ return '<a href="' + i[0] + '">' + i[1] + '</a>'; }).join("");
    m.addEventListener("click", function(e){
      var a = e.target.closest("a"); if (!a) return; var h = a.getAttribute("href"); m.remove();
      var map = {"#new": "newchat3", "#group": "newgroup3", "#sel": "sel3", "#priv": "gprivacy3"};
      if (map[h]){ e.preventDefault(); var b = $(map[h]); if (b) b.click(); }
      else if (h === "#xcqr"){ e.preventDefault(); qrSheet("me"); }
    });
    B.appendChild(m);
    setTimeout(function(){ D.addEventListener("click", function c(e){ if (!m.contains(e.target)){ m.remove(); D.removeEventListener("click", c, true); } }, true); }, 0);
  }
  D.addEventListener("click", function(e){
    var b = e.target.closest("[data-xc]"); if (!b) return;
    var k = b.getAttribute("data-xc");
    if (k === "qr"){ e.preventDefault(); qrSheet("me"); }
    else if (k === "menu"){ e.stopPropagation(); menu(); }
    else if (k === "search"){ srch.classList.toggle("on"); if (srch.classList.contains("on")) srch.querySelector("input").focus(); }
  });
  if (location.hash === "#xcqr") setTimeout(function(){ qrSheet("me"); }, 300);

  // ---------- QR ----------
  function loadJs(src, test){ return new Promise(function(ok){ if (test()) return ok(); var s = D.createElement("script"); s.src = src; s.onload = ok; s.onerror = ok; D.head.appendChild(s); }); }
  function qrCanvas(text, size){
    return loadJs("/js/qrgen-1.js", function(){ return typeof window.qrcode === "function"; }).then(function(){
      var q = window.qrcode(0, "M"); q.addData(text); q.make();
      var n = q.getModuleCount(), cell = Math.max(2, Math.floor(size / (n + 8))), pad = cell * 4, c = D.createElement("canvas");
      c.width = c.height = n * cell + pad * 2; var x = c.getContext("2d");
      x.fillStyle = "#fff"; x.fillRect(0, 0, c.width, c.height); x.fillStyle = "#0D1424";
      for (var r = 0; r < n; r++) for (var k = 0; k < n; k++) if (q.isDark(r, k)) x.fillRect(pad + k * cell, pad + r * cell, cell, cell);
      var lg = new Image(); lg.src = "/brand/xpertchat/mark-128.webp";
      return new Promise(function(ok){ lg.onload = function(){ var s = c.width * .2, o = (c.width - s) / 2; x.fillStyle = "#fff"; x.fillRect(o - 6, o - 6, s + 12, s + 12); x.drawImage(lg, o, o, s, s); ok(c); }; lg.onerror = function(){ ok(c); }; });
    });
  }
  function sheet(title){
    var w = D.createElement("div"); w.className = "xcsheet"; w.innerHTML = '<div><div class="sh"><b>' + title + '</b><button type="button" aria-label="Close">&times;</button></div><div class="sb"></div></div>';
    var stop = [];
    var close = function(){ stop.forEach(function(f){ try { f(); } catch (e) {} }); w.remove(); };
    w.addEventListener("click", function(e){ if (e.target === w || e.target.closest(".sh button")) close(); });
    B.appendChild(w); return {el: w.querySelector(".sb"), close: close, onClose: function(f){ stop.push(f); }};
  }
  function qrShow(box, url, label, file){
    box.innerHTML = '<div class="qrbox"><div id="xcq">Making the code…</div><p>' + label + '</p><div><button class="bt p" data-dl>⬇ Save picture</button><button class="bt" data-sh>🔗 Share link</button></div><p style="word-break:break-all;font-size:12px">' + esc(url) + '</p></div>';
    qrCanvas(url, 600).then(function(c){ var q = box.querySelector("#xcq"); if (!q) return; q.innerHTML = ""; q.appendChild(c);
      box.querySelector("[data-dl]").onclick = function(){ var a = D.createElement("a"); a.href = c.toDataURL("image/png"); a.download = file + ".png"; a.click(); }; });
    box.querySelector("[data-sh]").onclick = function(){ if (navigator.share) navigator.share({title: label, url: url}).catch(function(){}); else { navigator.clipboard && navigator.clipboard.writeText(url); this.textContent = "✔ Copied"; } };
  }
  function qrSheet(tab){
    var s = sheet("▦ XpertChat QR code");
    var draw = function(t){
      s.el.innerHTML = '<div class="tb"><button data-t="me" class="' + (t === "me" ? "on" : "") + '">My code</button><button data-t="scan" class="' + (t === "scan" ? "on" : "") + '">Scan a code</button></div><div class="tbb"></div>';
      var box = s.el.querySelector(".tbb");
      s.el.querySelectorAll("[data-t]").forEach(function(b){ b.onclick = function(){ draw(b.getAttribute("data-t")); }; });
      if (t === "me"){
        box.innerHTML = '<p class="note">Loading…</p>';
        fetch("/api/network/me/", {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; }).then(function(me){
          if (!me || !me.slug){ box.innerHTML = '<p class="note">Sign in to get your QR code.</p><p style="text-align:center"><a class="bt p" href="/login?next=' + encodeURIComponent(location.href) + '">Sign in</a></p>'; return; }
          qrShow(box, "https://xpertcreation.com/in/" + me.slug + "?src=qr", "Let people scan this to open your profile and connect with you. Once you connect, you can chat.", "xpertchat-" + me.slug);
        });
      } else scanner(box, s);
    };
    draw(tab || "me");
  }
  function scanner(box, s){
    box.innerHTML = '<video playsinline muted></video><p class="note">Point the camera at an XpertCreation QR code: a profile, a group invite or a shop.</p><label class="bt" style="display:flex">🖼️ Scan from a picture<input type="file" accept="image/*" hidden></label><div class="note" id="xcqm"></div>';
    var v = box.querySelector("video"), stream = null, timer = null, done = false;
    var go = function(txt){
      if (done || !txt) return; done = true;
      var u = null; try { u = new URL(txt); } catch (e) {}
      if (u && /(^|\.)xpertcreation\.com$/.test(u.hostname)){ $("xcqm").textContent = "✔ Opening…"; s.close(); location.href = u.href; }
      else { done = false; $("xcqm").innerHTML = "This code is not an XpertCreation link:<br><b>" + esc(txt.slice(0, 200)) + "</b>"; }
    };
    var det = ("BarcodeDetector" in window) ? new window.BarcodeDetector({formats: ["qr_code"]}) : null;
    var read = function(src){
      if (det) return det.detect(src).then(function(r){ return r[0] && r[0].rawValue; }).catch(function(){ return null; });
      return loadJs("/js/jsqr-1.js", function(){ return typeof window.jsQR === "function"; }).then(function(){
        var c = D.createElement("canvas"), w = src.videoWidth || src.naturalWidth || src.width, h = src.videoHeight || src.naturalHeight || src.height; if (!w) return null;
        var sc = Math.min(1, 800 / w); c.width = w * sc; c.height = h * sc; var x = c.getContext("2d"); x.drawImage(src, 0, 0, c.width, c.height);
        var r = window.jsQR && window.jsQR(x.getImageData(0, 0, c.width, c.height).data, c.width, c.height); return r && r.data;
      });
    };
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia){
      navigator.mediaDevices.getUserMedia({video: {facingMode: "environment"}}).then(function(st){
        stream = st; v.srcObject = st; v.play();
        timer = setInterval(function(){ if (v.readyState >= 2) read(v).then(go); }, 450);
      }).catch(function(){ $("xcqm").textContent = "Camera not allowed. Use 'Scan from a picture' instead."; });
    } else $("xcqm").textContent = "This browser can't open the camera. Use 'Scan from a picture'.";
    s.onClose(function(){ clearInterval(timer); if (stream) stream.getTracks().forEach(function(t){ t.stop(); }); });
    box.querySelector("input[type=file]").onchange = function(){ var f = this.files[0]; if (!f) return; var im = new Image(); im.onload = function(){ read(im).then(function(t){ if (t) go(t); else $("xcqm").textContent = "No QR code found in that picture."; }); }; im.src = URL.createObjectURL(f); };
  }
  // group invite link -> QR code button (group.html, admins)
  function groupQR(){
    var lb = $("glinkbox"); if (!lb || lb.querySelector(".xcgqr")) return;
    var b = lb.querySelector("b"); if (!b || !/group\/join\//.test(b.textContent)) return;
    var url = b.textContent.trim(); if (url.charAt(0) === "/") url = "https://xpertcreation.com" + url;
    var btn = D.createElement("button"); btn.className = "gbtn xcgqr"; btn.type = "button"; btn.textContent = "▦ QR code";
    btn.onclick = function(){ var s = sheet("▦ Group QR code"); var nm = (D.querySelector("#gv h1, #gv h2, #gv b") || {}).textContent || "the group";
      qrShow(s.el, url, "Anyone who scans this joins " + esc(nm.trim().slice(0, 60)) + ". Print it or share it.", "group-qr"); };
    var acts = lb.querySelector(".gacts"); (acts || lb).appendChild(btn);
  }

  // ---------- my stickers (chat.html) ----------
  if (page !== "chat") return;
  var KEY = "xc_mystk_v1", MAX = 24;
  function mine(){ try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch (e) { return []; } }
  function keep(a){ try { localStorage.setItem(KEY, JSON.stringify(a.slice(0, MAX))); return true; } catch (e) { alert("Your phone's sticker space is full. Remove a few stickers first."); return false; } }
  window.XCStk = {grid: function(){
    var a = mine();
    return '<div class="xcmy' + (window.XCStkEdit ? ' edit' : '') + '"><button type="button" class="mk" data-mkstk><span>➕</span>Make a sticker</button>'
      + a.map(function(s, i){ return '<button type="button" data-mystk="' + i + '"><img src="' + s + '" alt="My sticker"><span class="rm" data-rmstk="' + i + '">×</span></button>'; }).join("") + '</div>'
      + (a.length ? '<p style="text-align:right;margin:6px 0 0"><button type="button" data-edstk style="border:0;background:none;color:#1B4DFF;font-weight:700;cursor:pointer">' + (window.XCStkEdit ? "Done" : "Remove stickers") + '</button></p>' : '<p style="font-size:12.5px;color:#5A657C;margin:6px 2px 0">Turn any photo into a sticker: crop it, cut out a plain background and add words. Stickers stay on this phone.</p>');
  }};
  function redraw(){ var et = D.querySelector('[data-etab="mine"]'); if (et) et.click(); }
  D.addEventListener("click", function(e){
    if (e.target.closest("[data-mkstk]")){ e.stopPropagation(); maker(); return; }
    if (e.target.closest("[data-edstk]")){ e.stopPropagation(); window.XCStkEdit = !window.XCStkEdit; redraw(); return; }
    var rm = e.target.closest("[data-rmstk]"); if (rm){ e.stopPropagation(); var a = mine(); a.splice(+rm.getAttribute("data-rmstk"), 1); keep(a); redraw(); return; }
    var s = e.target.closest("[data-mystk]"); if (s){ e.stopPropagation(); sendMine(mine()[+s.getAttribute("data-mystk")]); }
  }, true);
  function sendMine(data){
    var cur = window.XC3 && XC3.cur && XC3.cur(); if (!cur || !data) return;
    fetch(data).then(function(r){ return r.blob(); }).then(function(bl){
      var fd = new FormData(); fd.append("photo", bl, "sticker." + (bl.type === "image/png" ? "png" : "webp")); fd.append("message", "[sticker:me]");
      return fetch("/api/notify/threads/" + cur.id + "/", {method: "POST", credentials: "same-origin", headers: {"X-CSRFToken": ck("xc_csrf")}, body: fd});
    }).then(function(r){ return r.json().then(function(d){ return {ok: r.ok, d: d}; }); }).then(function(r){
      if (!r.ok){ alert(r.d.detail || "Could not send the sticker."); return; }
      var em = $("emo3"); if (em) em.classList.remove("on");
      if (r.d.message && XC3.add) XC3.add([r.d.message]);
    });
  }
  function maker(){
    var s = sheet("✨ Make a sticker"), el = s.el;
    el.innerHTML = '<div class="stkmk"><canvas width="512" height="512"></canvas>'
      + '<div class="row"><label class="bt p" style="margin:0">📷 Choose a photo<input type="file" accept="image/*" hidden></label></div>'
      + '<div class="row" data-g="shape"><button data-v="circle" class="on">⚪ Circle</button><button data-v="round">▢ Rounded</button><button data-v="cut">✂️ Cut out background</button></div>'
      + '<div class="row"><span style="font-size:13px;color:#5A657C">Zoom</span><input type="range" min="60" max="300" value="100" data-k="zoom"></div>'
      + '<input type="text" maxlength="24" placeholder="Words on the sticker (optional)" data-k="txt">'
      + '<div class="row" data-g="pos"><button data-v="bottom" class="on">Words at bottom</button><button data-v="top">Words at top</button></div>'
      + '<p class="note">Drag the photo to move it. "Cut out background" works best on a plain wall or sky behind the person.</p>'
      + '<div class="row"><button class="bt g" data-save style="padding:12px 22px">✔ Save sticker</button></div></div>';
    var c = el.querySelector("canvas"), x = c.getContext("2d"), img = null, st = {shape: "circle", pos: "bottom", zoom: 1, dx: 0, dy: 0, txt: ""}, cutMask = null;
    function render(out){
      x.clearRect(0, 0, 512, 512);
      if (!img){ x.fillStyle = "#5A657C"; x.font = "bold 22px system-ui,sans-serif"; x.textAlign = "center"; x.fillText("Choose a photo", 256, 262); return; }
      var pad = 26, R = 256 - pad, sz = 512 - pad * 2;
      var lay = D.createElement("canvas"); lay.width = lay.height = 512; var l = lay.getContext("2d");
      var sc = Math.max(sz / img.width, sz / img.height) * st.zoom, w = img.width * sc, h = img.height * sc;
      l.save();
      if (st.shape === "circle"){ l.beginPath(); l.arc(256, 256, R, 0, Math.PI * 2); l.clip(); }
      else if (st.shape === "round"){ rr(l, pad, pad, sz, sz, 70); l.clip(); }
      l.drawImage(st.shape === "cut" && cutMask ? cutMask : img, 256 - w / 2 + st.dx, 256 - h / 2 + st.dy, w, h);
      l.restore();
      // white sticker outline around whatever is visible
      var o = D.createElement("canvas"); o.width = o.height = 512; var oc = o.getContext("2d");
      for (var a = 0; a < 360; a += 30){ var r = 9; oc.drawImage(lay, Math.cos(a * Math.PI / 180) * r, Math.sin(a * Math.PI / 180) * r); }
      oc.globalCompositeOperation = "source-in"; oc.fillStyle = "#fff"; oc.fillRect(0, 0, 512, 512);
      x.save(); x.shadowColor = "rgba(13,20,36,.28)"; x.shadowBlur = 10; x.shadowOffsetY = 3; x.drawImage(o, 0, 0); x.restore();
      x.drawImage(lay, 0, 0);
      if (st.txt){
        var y = st.pos === "top" ? 70 : 462, fs = Math.min(72, Math.floor(900 / Math.max(6, st.txt.length)));
        x.font = "900 " + fs + "px system-ui,'Segoe UI',Arial,sans-serif"; x.textAlign = "center"; x.textBaseline = "middle"; x.lineJoin = "round";
        x.lineWidth = Math.max(8, fs / 5); x.strokeStyle = "#0D1424"; x.strokeText(st.txt, 256, y); x.fillStyle = "#fff"; x.fillText(st.txt, 256, y);
      }
    }
    function rr(l, X, Y, W, H, r){ l.beginPath(); l.moveTo(X + r, Y); l.arcTo(X + W, Y, X + W, Y + H, r); l.arcTo(X + W, Y + H, X, Y + H, r); l.arcTo(X, Y + H, X, Y, r); l.arcTo(X, Y, X + W, Y, r); l.closePath(); }
    function cut(){   // flood fill from the edges: removes a plain background
      var w = img.width, h = img.height, k = Math.min(1, 700 / Math.max(w, h)); w = Math.round(w * k); h = Math.round(h * k);
      var cv = D.createElement("canvas"); cv.width = w; cv.height = h; var g = cv.getContext("2d"); g.drawImage(img, 0, 0, w, h);
      var id = g.getImageData(0, 0, w, h), p = id.data, seen = new Uint8Array(w * h), stack = [];
      var ref = function(i){ return [p[i * 4], p[i * 4 + 1], p[i * 4 + 2]]; };
      for (var i = 0; i < w; i++){ stack.push(i, (h - 1) * w + i); } for (var j = 0; j < h; j++){ stack.push(j * w, j * w + w - 1); }
      var refs = [ref(0), ref(w - 1), ref((h - 1) * w), ref(h * w - 1), ref(Math.floor(w / 2))], T = 46 * 46 * 3;
      var near = function(i){ var r = p[i * 4], gg = p[i * 4 + 1], b = p[i * 4 + 2]; for (var q = 0; q < refs.length; q++){ var a = refs[q], d = (r - a[0]) * (r - a[0]) + (gg - a[1]) * (gg - a[1]) + (b - a[2]) * (b - a[2]); if (d < T) return true; } return false; };
      while (stack.length){ var n = stack.pop(); if (seen[n]) continue; seen[n] = 1; if (!near(n)) continue; p[n * 4 + 3] = 0;
        var X = n % w, Y = (n / w) | 0; if (X > 0) stack.push(n - 1); if (X < w - 1) stack.push(n + 1); if (Y > 0) stack.push(n - w); if (Y < h - 1) stack.push(n + w); }
      g.putImageData(id, 0, 0); cutMask = cv;
    }
    el.querySelector("input[type=file]").onchange = function(){ var f = this.files[0]; if (!f) return; var im = new Image(); im.onload = function(){ img = im; cutMask = null; st.dx = st.dy = 0; if (st.shape === "cut") cut(); render(); }; im.src = URL.createObjectURL(f); };
    el.querySelectorAll("[data-g] button").forEach(function(b){ b.onclick = function(){ var g = b.parentNode.getAttribute("data-g"); b.parentNode.querySelectorAll("button").forEach(function(z){ z.classList.toggle("on", z === b); }); st[g] = b.getAttribute("data-v"); if (g === "shape" && st.shape === "cut" && img && !cutMask) cut(); render(); }; });
    el.querySelector('[data-k="zoom"]').oninput = function(){ st.zoom = this.value / 100; render(); };
    el.querySelector('[data-k="txt"]').oninput = function(){ st.txt = this.value.trim(); render(); };
    var drag = null;
    c.addEventListener("pointerdown", function(e){ drag = {x: e.clientX, y: e.clientY, dx: st.dx, dy: st.dy}; c.setPointerCapture(e.pointerId); });
    c.addEventListener("pointermove", function(e){ if (!drag) return; var k = 512 / c.getBoundingClientRect().width; st.dx = drag.dx + (e.clientX - drag.x) * k; st.dy = drag.dy + (e.clientY - drag.y) * k; render(); });
    c.addEventListener("pointerup", function(){ drag = null; });
    el.querySelector("[data-save]").onclick = function(){
      if (!img){ alert("Choose a photo first."); return; }
      render();
      var sm = D.createElement("canvas"); sm.width = sm.height = 320; sm.getContext("2d").drawImage(c, 0, 0, 320, 320);
      var data = sm.toDataURL("image/webp", .86); if (data.indexOf("data:image/webp") !== 0) data = sm.toDataURL("image/png");
      var a = mine(); a.unshift(data); if (keep(a)){ s.close(); redraw(); }
    };
    render();
  }
})();
