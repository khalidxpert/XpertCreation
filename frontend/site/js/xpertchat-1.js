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

  // ---------- my stickers: chats (chat.html) and groups (group.html) ----------
  if (page !== "chat" && page !== "group") return;
  var BUILTIN = "salam jazakallah shukriya mubarak inshaallah mashaallah alhamdulillah ameen eid ramadan ok thanks congrats welcome goodnight haha".split(" ");
  var MY = null, loading = null;
  function api(p, opt){ opt = opt || {}; var h = {"X-CSRFToken": ck("xc_csrf")}; if (opt.json){ h["Content-Type"] = "application/json"; }
    return fetch("/api/notify/stickers/" + p, {method: opt.method || "GET", credentials: "same-origin", headers: h, body: opt.json ? JSON.stringify(opt.json) : opt.body})
      .then(function(r){ return r.json().catch(function(){ return {}; }).then(function(d){ return {ok: r.ok, d: d}; }); }); }
  function load(){
    if (loading) return loading;
    loading = api("mine/").then(function(r){ MY = r.ok ? (r.d.stickers || []) : []; migrate(); refresh(); return MY; });
    return loading;
  }
  function migrate(){   // stickers made before (kept only on this phone) move to the server, so they show on every device
    var old; try { old = JSON.parse(localStorage.getItem("xc_mystk_v1") || "[]"); } catch (e) { old = []; }
    if (!old.length) return;
    try { localStorage.removeItem("xc_mystk_v1"); } catch (e) {}
    old.reverse().reduce(function(p, data){ return p.then(function(){ return fetch(data).then(function(r){ return r.blob(); }).then(function(b){ var fd = new FormData(); fd.append("file", b, "s.webp"); return api("mine/", {method: "POST", body: fd}); }).then(function(r){ if (r.ok) MY = r.d.stickers; }); }); }, Promise.resolve()).then(refresh);
  }
  function refresh(){ var et = D.querySelector('#emo3 [data-etab="mine"].on'); if (et) et.click(); var g = D.querySelector(".xcgp .egs"); if (g) g.innerHTML = gridHtml(); }
  function gridHtml(){
    if (!MY){ load(); return '<p style="color:#5A657C;font-size:13px">Loading…</p>'; }
    return '<div class="xcmy' + (window.XCStkEdit ? ' edit' : '') + '"><button type="button" class="mk" data-mkstk><span>➕</span>Make a sticker</button>'
      + MY.map(function(s){ return '<button type="button" data-mystk="' + esc(s.url) + '"><img src="' + esc(s.url) + '" alt="My sticker" loading="lazy">' + (s.anim ? '<i class="an">GIF</i>' : '') + '<span class="rm" data-rmstk="' + esc(s.name) + '">×</span></button>'; }).join("") + '</div>'
      + (MY.length ? '<p style="text-align:right;margin:6px 0 0"><button type="button" data-edstk style="border:0;background:none;color:#1B4DFF;font-weight:700;cursor:pointer">' + (window.XCStkEdit ? "Done" : "Remove stickers") + '</button></p>'
        : '<p style="font-size:12.5px;color:#5A657C;margin:6px 2px 0">Turn a photo or a few seconds of video into your own sticker. They show on every phone you sign in on.</p>');
  }
  window.XCStk = {grid: gridHtml};
  load();
  D.addEventListener("click", function(e){
    if (e.target.closest("[data-mkstk]")){ e.stopPropagation(); maker(); return; }
    if (e.target.closest("[data-edstk]")){ e.stopPropagation(); window.XCStkEdit = !window.XCStkEdit; refresh(); return; }
    var rm = e.target.closest("[data-rmstk]"); if (rm){ e.stopPropagation(); api("mine/" + rm.getAttribute("data-rmstk") + "/", {method: "DELETE"}).then(function(r){ if (r.ok){ MY = r.d.stickers; refresh(); } }); return; }
    var s = e.target.closest("[data-mystk]"); if (s){ e.stopPropagation(); sendUrl(s.getAttribute("data-mystk")); return; }
    var b = e.target.closest("[data-gstk]"); if (b){ e.stopPropagation(); if (window.XCG) XCG.send("[sticker:" + b.getAttribute("data-gstk") + "]"); closeGP(); }
  }, true);
  function sendUrl(url){
    fetch(url, {credentials: "same-origin"}).then(function(r){ return r.blob(); }).then(function(bl){
      var file = new File([bl], "sticker.webp", {type: bl.type || "image/webp"});
      if (page === "group"){ if (window.XCG) XCG.send("[sticker:me]", file); closeGP(); return; }
      var cur = window.XC3 && XC3.cur && XC3.cur(); if (!cur) return;
      var fd = new FormData(); fd.append("photo", file); fd.append("message", "[sticker:me]");
      return fetch("/api/notify/threads/" + cur.id + "/", {method: "POST", credentials: "same-origin", headers: {"X-CSRFToken": ck("xc_csrf")}, body: fd})
        .then(function(r){ return r.json().then(function(d){ return {ok: r.ok, d: d}; }); }).then(function(r){
          if (!r.ok){ alert(r.d.detail || "Could not send the sticker."); return; }
          var em = $("emo3"); if (em) em.classList.remove("on");
          if (r.d.message && XC3.add) XC3.add([r.d.message]);
        });
    });
  }
  // groups: a sticker button next to the message box
  function closeGP(){ var g = D.querySelector(".xcgp"); if (g) g.remove(); }
  if (page === "group"){
    var putBtn = function(){
      var q = $("gq"); if (!q || D.getElementById("xcgstk")) return;
      var b = D.createElement("button"); b.type = "button"; b.id = "xcgstk"; b.className = "gmic"; b.setAttribute("aria-label", "Stickers"); b.textContent = "😀";
      q.parentNode.insertBefore(b, q);
      b.onclick = function(){
        if (D.querySelector(".xcgp")){ closeGP(); return; }
        var p = D.createElement("div"); p.className = "xcgp";
        var tab = "mine", draw = function(){
          p.innerHTML = '<div class="etabs"><button data-gt="mine" class="' + (tab === "mine" ? "on" : "") + '">✨ My stickers</button><button data-gt="stk" class="' + (tab === "stk" ? "on" : "") + '">Stickers</button><button data-gt="x" style="margin-left:auto">×</button></div><div class="egs">'
            + (tab === "mine" ? gridHtml() : '<div class="stkgrid">' + BUILTIN.map(function(s){ return '<button type="button" data-gstk="' + s + '"><img src="/stickers/' + s + '.svg" alt="' + s + '" loading="lazy"></button>'; }).join("") + '</div>') + '</div>';
          p.querySelectorAll("[data-gt]").forEach(function(t){ t.onclick = function(){ var v = t.getAttribute("data-gt"); if (v === "x"){ closeGP(); return; } tab = v; draw(); }; });
        };
        draw(); var bar2 = q.closest("div"); bar2.parentNode.insertBefore(p, bar2);
      };
    };
    new MutationObserver(putBtn).observe(B, {childList: true, subtree: true}); putBtn();
  }

  // ---------- the sticker maker: photo or video, words with colour, size and font ----------
  var FONTS = [["Bold", "900 {s}px system-ui,'Segoe UI',Arial,sans-serif"], ["Round", "800 {s}px 'Baloo 2',system-ui,sans-serif"], ["Fun", "400 {s}px Pacifico,'Comic Sans MS',cursive"],
               ["Classic", "700 {s}px Georgia,'Times New Roman',serif"], ["Poster", "400 {s}px Bangers,Impact,'Arial Black',sans-serif"], ["اردو", "700 {s}px 'Noto Nastaliq Urdu',serif"]];
  var COLORS = ["#FFFFFF", "#0D1424", "#FACC15", "#EF4444", "#22C55E", "#3B82F6", "#EC4899", "#F97316"];
  function fontsReady(){
    if (!D.getElementById("xcstkfonts")){ var l = D.createElement("link"); l.id = "xcstkfonts"; l.rel = "stylesheet"; l.href = "https://fonts.googleapis.com/css2?family=Baloo+2:wght@800&family=Bangers&family=Noto+Nastaliq+Urdu:wght@700&family=Pacifico&display=swap"; D.head.appendChild(l); }
    return D.fonts && D.fonts.load ? Promise.all(["800 40px 'Baloo 2'", "40px Bangers", "40px Pacifico", "700 40px 'Noto Nastaliq Urdu'"].map(function(f){ return D.fonts.load(f).catch(function(){}); })) : Promise.resolve();
  }
  function maker(){
    var s = sheet("✨ Make a sticker"), el = s.el;
    el.innerHTML = '<div class="stkmk"><div class="tb"><button data-mode="photo" class="on">📷 From a photo</button><button data-mode="video">🎬 Animated, from a video</button></div>'
      + '<div class="cvw"><canvas width="512" height="512"></canvas><video playsinline muted loop hidden></video></div>'
      + '<div class="row"><label class="bt p" style="margin:0"><span data-pick>📷 Choose a photo</span><input type="file" accept="image/*" hidden></label></div>'
      + '<div class="row" data-g="shape"><button data-v="circle" class="on">⚪ Circle</button><button data-v="round">▢ Rounded</button><button data-v="cut" data-only="photo">✂️ Cut out background</button><button data-v="full" data-only="video">⬛ Square</button></div>'
      + '<div class="row"><span class="lb">Zoom</span><input type="range" min="60" max="300" value="100" data-k="zoom"></div>'
      + '<div class="vrow" hidden><div class="row"><span class="lb">Start at</span><input type="range" min="0" max="100" value="0" step="0.1" data-k="start"><b data-k="startl">0.0s</b></div>'
      + '<div class="row" data-g="dur"><span class="lb">Length</span><button data-v="2">2 s</button><button data-v="3" class="on">3 s</button><button data-v="4">4 s</button><button data-v="5">5 s</button></div></div>'
      + '<input type="text" maxlength="28" placeholder="Words on the sticker (optional) — English or اردو" data-k="txt">'
      + '<div class="row sw" data-g="color">' + COLORS.map(function(c, i){ return '<button data-v="' + c + '" class="' + (i ? "" : "on") + '" style="background:' + c + '" aria-label="Colour"></button>'; }).join("") + '</div>'
      + '<div class="row" data-g="font">' + FONTS.map(function(f, i){ return '<button data-v="' + i + '" class="' + (i ? "" : "on") + '">' + f[0] + '</button>'; }).join("") + '</div>'
      + '<div class="row" data-g="size"><button data-v="s">Small</button><button data-v="m" class="on">Medium</button><button data-v="l">Big</button></div>'
      + '<div class="row" data-g="pos"><button data-v="bottom" class="on">Words at bottom</button><button data-v="middle">Middle</button><button data-v="top">Top</button></div>'
      + '<p class="note" data-tip>Drag the photo to move it. "Cut out background" works best on a plain wall or sky behind the person.</p>'
      + '<div class="row"><button class="bt g" data-save style="padding:12px 22px">✔ Save sticker</button></div><div class="note" data-msg></div></div>';
    var c = el.querySelector("canvas"), x = c.getContext("2d"), vid = el.querySelector("video"), file = null, img = null, cutMask = null, raf = 0;
    var st = {mode: "photo", shape: "circle", pos: "bottom", zoom: 1, dx: 0, dy: 0, txt: "", color: COLORS[0], font: 0, size: "m", start: 0, dur: 3};
    s.onClose(function(){ cancelAnimationFrame(raf); try { vid.pause(); URL.revokeObjectURL(vid.src); } catch (e) {} });
    function src(){ return st.mode === "video" ? (vid.videoWidth ? vid : null) : img; }
    function dims(o){ return o === vid ? [vid.videoWidth, vid.videoHeight] : [o.width, o.height]; }
    function rr(l, X, Y, W, H, r){ l.beginPath(); l.moveTo(X + r, Y); l.arcTo(X + W, Y, X + W, Y + H, r); l.arcTo(X + W, Y + H, X, Y + H, r); l.arcTo(X, Y + H, X, Y, r); l.arcTo(X, Y, X + W, Y, r); l.closePath(); }
    function words(g){   // the words layer (also sent to the server for animated stickers)
      if (!st.txt) return;
      var len = Math.max(5, st.txt.length), base = {s: 560, m: 760, l: 980}[st.size], fs = Math.max(26, Math.min({s: 52, m: 72, l: 96}[st.size], Math.floor(base / len)));
      var y = st.pos === "top" ? 70 : (st.pos === "middle" ? 256 : 458), dark = st.color === "#0D1424";
      g.font = FONTS[st.font][1].replace("{s}", fs); g.textAlign = "center"; g.textBaseline = "middle"; g.lineJoin = "round";
      if (FONTS[st.font][0].charCodeAt(0) > 1500) g.direction = "rtl";
      g.lineWidth = Math.max(8, fs / 4.5); g.strokeStyle = dark ? "#FFFFFF" : "#0D1424"; g.strokeText(st.txt, 256, y, 480);
      g.fillStyle = st.color; g.fillText(st.txt, 256, y, 480); g.direction = "ltr";
    }
    function render(){
      x.clearRect(0, 0, 512, 512);
      var o = src();
      if (!o){ x.fillStyle = "#5A657C"; x.font = "bold 22px system-ui,sans-serif"; x.textAlign = "center"; x.fillText(st.mode === "video" ? "Choose a video" : "Choose a photo", 256, 262); return; }
      var pad = 26, R = 256 - pad, sz = 512 - pad * 2, dd = dims(o), sc = Math.max(sz / dd[0], sz / dd[1]) * st.zoom, w = dd[0] * sc, h = dd[1] * sc;
      var lay = D.createElement("canvas"); lay.width = lay.height = 512; var l = lay.getContext("2d");
      l.save();
      if (st.shape === "circle"){ l.beginPath(); l.arc(256, 256, R, 0, Math.PI * 2); l.clip(); }
      else if (st.shape === "round"){ rr(l, pad, pad, sz, sz, 70); l.clip(); }
      else if (st.shape === "full"){ l.beginPath(); l.rect(pad, pad, sz, sz); l.clip(); }
      l.drawImage(st.shape === "cut" && cutMask ? cutMask : o, 256 - w / 2 + st.dx, 256 - h / 2 + st.dy, w, h);
      l.restore();
      if (st.mode === "photo"){
        var ol = D.createElement("canvas"); ol.width = ol.height = 512; var oc = ol.getContext("2d");
        for (var a = 0; a < 360; a += 30) oc.drawImage(lay, Math.cos(a * Math.PI / 180) * 9, Math.sin(a * Math.PI / 180) * 9);
        oc.globalCompositeOperation = "source-in"; oc.fillStyle = "#fff"; oc.fillRect(0, 0, 512, 512);
        x.save(); x.shadowColor = "rgba(13,20,36,.28)"; x.shadowBlur = 10; x.shadowOffsetY = 3; x.drawImage(ol, 0, 0); x.restore();
      }
      x.drawImage(lay, 0, 0); words(x);
    }
    function loop(){ cancelAnimationFrame(raf); var tick = function(){ if (st.mode === "video" && vid.videoWidth){ if (vid.currentTime > st.start + st.dur || vid.currentTime < st.start - .3) vid.currentTime = st.start; render(); } raf = requestAnimationFrame(tick); }; tick(); }
    function cut(){
      var w = img.width, h = img.height, k = Math.min(1, 700 / Math.max(w, h)); w = Math.round(w * k); h = Math.round(h * k);
      var cv = D.createElement("canvas"); cv.width = w; cv.height = h; var g = cv.getContext("2d"); g.drawImage(img, 0, 0, w, h);
      var id = g.getImageData(0, 0, w, h), p = id.data, seen = new Uint8Array(w * h), stack = [];
      var ref = function(i){ return [p[i * 4], p[i * 4 + 1], p[i * 4 + 2]]; };
      for (var i = 0; i < w; i++) stack.push(i, (h - 1) * w + i); for (var j = 0; j < h; j++) stack.push(j * w, j * w + w - 1);
      var refs = [ref(0), ref(w - 1), ref((h - 1) * w), ref(h * w - 1), ref(Math.floor(w / 2))], T = 46 * 46 * 3;
      var near = function(i){ var r = p[i * 4], gg = p[i * 4 + 1], b = p[i * 4 + 2]; for (var q = 0; q < refs.length; q++){ var a = refs[q], d = (r - a[0]) * (r - a[0]) + (gg - a[1]) * (gg - a[1]) + (b - a[2]) * (b - a[2]); if (d < T) return true; } return false; };
      while (stack.length){ var n = stack.pop(); if (seen[n]) continue; seen[n] = 1; if (!near(n)) continue; p[n * 4 + 3] = 0;
        var X = n % w, Y = (n / w) | 0; if (X > 0) stack.push(n - 1); if (X < w - 1) stack.push(n + 1); if (Y > 0) stack.push(n - w); if (Y < h - 1) stack.push(n + w); }
      g.putImageData(id, 0, 0); cutMask = cv;
    }
    function setMode(m){
      st.mode = m; st.dx = st.dy = 0; file = null; img = null; cutMask = null; vid.removeAttribute("src");
      el.querySelectorAll("[data-mode]").forEach(function(b){ b.classList.toggle("on", b.getAttribute("data-mode") === m); });
      el.querySelector("[data-pick]").textContent = m === "video" ? "🎬 Choose a video" : "📷 Choose a photo";
      el.querySelector("input[type=file]").accept = m === "video" ? "video/*" : "image/*";
      el.querySelector(".vrow").hidden = m !== "video";
      el.querySelectorAll("[data-only]").forEach(function(b){ b.hidden = b.getAttribute("data-only") !== m; });
      if (st.shape === "cut" && m === "video" || st.shape === "full" && m === "photo") el.querySelector('[data-g="shape"] [data-v="circle"]').click();
      el.querySelector("[data-tip]").textContent = m === "video" ? "Pick the part you want (2 to 5 seconds). Drag to move, zoom to fit. The sticker plays again and again, with no sound." : 'Drag the photo to move it. "Cut out background" works best on a plain wall or sky behind the person.';
      render(); if (m === "video") loop(); else cancelAnimationFrame(raf);
    }
    el.querySelectorAll("[data-mode]").forEach(function(b){ b.onclick = function(){ setMode(b.getAttribute("data-mode")); }; });
    el.querySelector("input[type=file]").onchange = function(){
      var f = this.files[0]; if (!f) return; file = f;
      if (st.mode === "video"){
        if (f.size > 40 * 1024 * 1024){ alert("That video is over 40 MB. Choose a shorter one."); return; }
        vid.src = URL.createObjectURL(f); vid.onloadedmetadata = function(){ var r = el.querySelector('[data-k="start"]'); r.max = Math.max(0, (vid.duration || 0) - 1).toFixed(1); st.start = 0; r.value = 0; vid.currentTime = 0; vid.play().catch(function(){}); loop(); };
      } else { var im = new Image(); im.onload = function(){ img = im; cutMask = null; st.dx = st.dy = 0; if (st.shape === "cut") cut(); render(); }; im.src = URL.createObjectURL(f); }
    };
    el.querySelectorAll("[data-g] button").forEach(function(b){ b.onclick = function(){ var g = b.parentNode.getAttribute("data-g"); b.parentNode.querySelectorAll("button").forEach(function(z){ z.classList.toggle("on", z === b); });
      var v = b.getAttribute("data-v"); st[g] = g === "dur" ? +v : (g === "font" ? +v : v);
      if (g === "shape" && v === "cut" && img && !cutMask) cut(); if (g === "dur") vid.currentTime = st.start; render(); }; });
    el.querySelector('[data-k="zoom"]').oninput = function(){ st.zoom = this.value / 100; render(); };
    el.querySelector('[data-k="txt"]').oninput = function(){ st.txt = this.value.trim(); render(); };
    el.querySelector('[data-k="start"]').oninput = function(){ st.start = +this.value; el.querySelector('[data-k="startl"]').textContent = st.start.toFixed(1) + "s"; vid.currentTime = st.start; };
    var drag = null;
    c.addEventListener("pointerdown", function(e){ drag = {x: e.clientX, y: e.clientY, dx: st.dx, dy: st.dy}; c.setPointerCapture(e.pointerId); });
    c.addEventListener("pointermove", function(e){ if (!drag) return; var k = 512 / c.getBoundingClientRect().width; st.dx = drag.dx + (e.clientX - drag.x) * k; st.dy = drag.dy + (e.clientY - drag.y) * k; render(); });
    c.addEventListener("pointerup", function(){ drag = null; });
    var msg = function(t, bad){ var m = el.querySelector("[data-msg]"); m.style.color = bad ? "#B91C1C" : "#5A657C"; m.textContent = t; };
    el.querySelector("[data-save]").onclick = function(){
      var btn = this;
      if (!src()){ msg(st.mode === "video" ? "Choose a video first." : "Choose a photo first.", true); return; }
      btn.disabled = true; render();
      if (st.mode === "photo"){
        var sm = D.createElement("canvas"); sm.width = sm.height = 384; sm.getContext("2d").drawImage(c, 0, 0, 384, 384);
        sm.toBlob(function(bl){ var fd = new FormData(); fd.append("file", bl, "sticker.webp");
          api("mine/", {method: "POST", body: fd}).then(function(r){ btn.disabled = false; if (!r.ok){ msg(r.d.detail || "Could not save.", true); return; } MY = r.d.stickers; s.close(); refresh(); }); }, "image/webp", .9);
        return;
      }
      // animated: the server cuts the clip; we send the crop, the shape and the words as a see-through picture
      var dd = dims(vid), pad = 26, sz = 512 - pad * 2, sc = Math.max(sz / dd[0], sz / dd[1]) * st.zoom;
      var cs = sz / sc, cx = dd[0] / 2 - st.dx / sc - cs / 2, cy = dd[1] / 2 - st.dy / sc - cs / 2;
      var ov = D.createElement("canvas"); ov.width = ov.height = 512; words(ov.getContext("2d"));
      msg("Making your animated sticker… (a few seconds)");
      ov.toBlob(function(ob){
        var fd = new FormData(); fd.append("clip", file); fd.append("overlay", ob, "words.png");
        fd.append("start", st.start); fd.append("dur", st.dur); fd.append("shape", st.shape === "round" ? "round" : (st.shape === "full" ? "full" : "circle"));
        fd.append("cx", Math.round(cx)); fd.append("cy", Math.round(cy)); fd.append("cs", Math.round(cs));
        api("make/", {method: "POST", body: fd}).then(function(r){ btn.disabled = false; if (!r.ok){ msg(r.d.detail || "Could not make the sticker.", true); return; } MY = r.d.stickers; s.close(); refresh(); });
      }, "image/png");
    };
    setMode("photo"); fontsReady().then(render);
  }
})();
