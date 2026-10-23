/* XpertCreation Video Translate (/video-translate): subtitles and a transcript for your own video, in any language.
   Upload a video (or paste a direct link to a video file), get subtitles, translate them, watch, copy or download (.srt / .vtt / .txt).
   The video is deleted from the server 2 hours after upload; the subtitles stay for 30 days. */
(function(){
  "use strict";
  var D = document, B = D.body, app = D.getElementById("xvt");
  if (!app) return;
  var API = "/api/vtr/", Q = new URLSearchParams(location.search), LOCAL = {}, INFO = null, CUR = null, pollT = null, busyUp = false;
  function esc(s){ return String(s == null ? "" : s).replace(/[&<>"']/g, function(c){ return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]; }); }
  function ck(n){ var m = D.cookie.match(new RegExp("(?:^|; )" + n + "=([^;]*)")); return m ? decodeURIComponent(m[1]) : ""; }
  function api(p, body, form){
    var o = {method: body || form ? "POST" : "GET", credentials: "same-origin", headers: {"X-CSRFToken": ck("xc_csrf")}};
    if (form) o.body = form; else if (body){ o.body = JSON.stringify(body); o.headers["Content-Type"] = "application/json"; }
    return fetch(API + p, o).then(function(r){ return r.json().catch(function(){ return {}; }).then(function(d){ d._s = r.status; d._ok = r.ok; return d; }); })
      .catch(function(){ return {_ok: false, _s: 0, detail: "No internet. Check your connection and try again."}; });
  }
  function toast(t){ var e = D.createElement("div"); e.className = "vx-toast"; e.textContent = t; B.appendChild(e); setTimeout(function(){ e.remove(); }, 3500); }
  function tm(s){ s = Math.max(0, Math.floor(s)); var h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = s % 60; return (h ? h + ":" + ("0" + m).slice(-2) : m) + ":" + ("0" + x).slice(-2); }
  function mb(n){ return n > 1073741824 ? (n / 1073741824).toFixed(2) + " GB" : Math.max(0.1, n / 1048576).toFixed(1) + " MB"; }
  function left(s){ var h = Math.floor(s / 3600), m = Math.ceil(s % 3600 / 60); return h ? h + " h " + m + " min" : m + " min"; }
  var RTL = ["ur", "ar", "pa", "ps", "sd", "fa"];

  var css = D.createElement("style");
  css.textContent = [
    "@font-face{font-family:'Noto Nastaliq Urdu';font-style:normal;font-weight:700;font-display:swap;src:url(/fonts/noto-nastaliq-urdu-700.woff2) format('woff2')}",
    ".vx{max-width:900px;width:100%;flex:1;margin:0 auto;padding:12px 15px 60px;box-sizing:border-box;color:#0D1424}",
    ".vx-hero{background:linear-gradient(135deg,#1E1B4B,#4338CA 55%,#0EA5E9);color:#fff;border-radius:22px;padding:20px 18px;margin-bottom:14px}",
    ".vx-hero h1{margin:0 0 2px;font-size:26px;letter-spacing:-.02em;font-family:var(--display,inherit);font-weight:800}.vx-hero p{margin:4px 0 0;opacity:.92;font-size:14px;line-height:1.5}",
    ".vx-ur{font-family:'Noto Nastaliq Urdu',serif;font-weight:700;direction:rtl;font-size:15px;line-height:2.1;opacity:.92}",
    ".vx-card{background:#fff;border:1px solid #E4E8F2;border-radius:18px;padding:15px;margin-top:12px}.vx-card h3{margin:0 0 8px;font-size:16px}",
    ".vx-seg{display:flex;gap:6px;margin-bottom:10px}.vx-seg button{flex:1;border:1.5px solid #E4E8F2;background:#fff;border-radius:12px;padding:10px;font:inherit;font-weight:800;font-size:14px;cursor:pointer;color:#0D1424}",
    ".vx-seg button.on{background:#0D1424;color:#fff;border-color:#0D1424}",
    ".vx-drop{display:block;border:2px dashed #C7D2FE;background:#EEF2FF;border-radius:16px;padding:22px 14px;text-align:center;cursor:pointer;color:#3730A3}",
    ".vx-drop b{display:block;font-size:16px;margin-top:4px}.vx-drop small{color:#5A657C}",
    ".vx-row{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}@media(max-width:520px){.vx-row{grid-template-columns:1fr}}",
    ".vx label.l{display:block;font-size:11.5px;font-weight:800;color:#5A657C;text-transform:uppercase;letter-spacing:.03em;margin-bottom:5px}",
    ".vx select,.vx input[type=url],.vx textarea{width:100%;box-sizing:border-box;padding:11px 12px;border:1.5px solid #E4E8F2;border-radius:12px;font:inherit;font-size:15px;background:#F6F7FB;color:#0D1424}",
    ".vx-btn{border:0;border-radius:13px;padding:12px 16px;font:inherit;font-weight:800;font-size:14.5px;cursor:pointer;background:#4338CA;color:#fff;text-decoration:none;display:inline-block;text-align:center}",
    ".vx-btn.g{background:#16A34A}.vx-btn.o{background:#fff;color:#0D1424;border:1.5px solid #E4E8F2}.vx-btn.r{background:#fff;color:#B91C1C;border:1.5px solid #FCA5A5}.vx-btn.s{padding:8px 11px;font-size:13px;border-radius:10px}",
    ".vx-btn:disabled{opacity:.5}.vx-go{width:100%;margin-top:12px}",
    ".vx-hint{font-size:12.5px;color:#5A657C;line-height:1.55;margin:8px 0 0}.vx-file{margin-top:10px;font-size:14px;background:#F6F7FB;border-radius:12px;padding:10px 12px}",
    ".vx-bar{height:10px;border-radius:9px;background:#E0E7FF;overflow:hidden;margin:10px 0 6px}.vx-bar i{display:block;height:100%;background:linear-gradient(90deg,#4338CA,#0EA5E9);width:0;transition:width .4s}",
    ".vx-note{background:#FFFBEB;border:1px solid #FDE68A;border-radius:14px;padding:10px 12px;font-size:13.5px;line-height:1.55;margin-top:12px}",
    ".vx-player{background:#000;border-radius:16px;overflow:hidden;margin-top:12px}.vx-player video{display:block;width:100%;max-height:70vh;background:#000}",
    "video::cue{font-family:'Noto Nastaliq Urdu','Segoe UI',system-ui,sans-serif;font-size:1.05em;line-height:1.7;background:rgba(0,0,0,.72);color:#fff}",
    ".vx-langs{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0 4px;align-items:center}.vx-langs button{border:1.5px solid #E4E8F2;background:#fff;border-radius:99px;padding:7px 12px;font:inherit;font-size:13px;font-weight:800;cursor:pointer}",
    ".vx-langs button.on{background:#4338CA;color:#fff;border-color:#4338CA}.vx-langs select{width:auto;padding:7px 10px;border-radius:99px;font-size:13px}",
    ".vx-acts{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}",
    ".vx-lines{max-height:58vh;overflow-y:auto;border:1px solid #EEF1F6;border-radius:14px;margin-top:10px;overscroll-behavior:contain}",
    ".vx-ln{display:flex;gap:10px;padding:9px 12px;border-bottom:1px solid #EEF1F6;cursor:pointer;align-items:flex-start}.vx-ln:last-child{border-bottom:0}",
    ".vx-ln small{font-family:ui-monospace,monospace;color:#4338CA;font-weight:700;flex:0 0 auto;padding-top:2px}.vx-ln p{margin:0;flex:1;font-size:15px;line-height:1.6}",
    ".vx-ln.rtl p{direction:rtl;text-align:right;font-family:'Noto Nastaliq Urdu',serif;line-height:2.1;font-size:15px}.vx-ln.on{background:#EEF2FF}",
    ".vx-ln .ed{border:0;background:none;cursor:pointer;opacity:.5;font-size:14px;padding:2px 4px}.vx-ln textarea{min-height:60px}",
    ".vx-job{display:flex;gap:10px;align-items:center;padding:10px 0;border-top:1px solid #EEF1F6}.vx-job:first-child{border-top:0}.vx-job .t{flex:1;min-width:0}",
    ".vx-job b{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.vx-job small{color:#5A657C}",
    ".vx-badge{font-size:11.5px;font-weight:800;border-radius:8px;padding:3px 8px;display:inline-block;background:#E0E7FF;color:#3730A3}.vx-badge.ok{background:#DCFCE7;color:#15803D}.vx-badge.bad{background:#FEE2E2;color:#B91C1C}",
    ".vx-toast{position:fixed;left:50%;bottom:110px;transform:translateX(-50%);background:#0D1424;color:#fff;padding:10px 16px;border-radius:12px;font-size:14px;z-index:2147483600;max-width:90%}",
    ".vx-yt{font-size:13.5px;line-height:1.6}.vx-yt ol{padding-left:20px;margin:6px 0}"
  ].join("\n");
  D.head.appendChild(css);

  function langOpts(sel, first){
    return (first ? '<option value="' + first[0] + '">' + first[1] + "</option>" : "") + (INFO ? INFO.langs : []).map(function(l){
      return '<option value="' + l.code + '"' + (l.code === sel ? " selected" : "") + ">" + esc(l.name) + (l.native !== l.name ? " · " + esc(l.native) : "") + "</option>"; }).join("");
  }
  function nameOf(c){ var l = (INFO ? INFO.langs : []).filter(function(x){ return x.code === c; })[0]; return l ? l.name : c; }

  /* ---------------------------------------------------------------- home: start a video + my videos */
  function home(){
    clearTimeout(pollT); CUR = null;
    var L = INFO.limits, mode = "file", file = null;
    app.innerHTML = '<div class="vx"><div class="vx-hero"><h1>🎬 Video Translate</h1><div class="vx-ur">ویڈیو کا ترجمہ — سب ٹائٹل کسی بھی زبان میں</div>'
      + "<p>Get subtitles and a full transcript for your video, then translate them into any language. Free.</p></div>"
      + (INFO.ai_ready ? "" : '<div class="vx-note">Video Translate is being switched on. Please try again a little later.</div>')
      + '<div class="vx-card"><h3>1. Your video</h3><div class="vx-seg"><button class="on" data-m="file">📁 Upload a video</button><button data-m="url">🔗 Paste a link</button></div>'
      + '<div data-box="file"><label class="vx-drop"><span style="font-size:30px">⬆️</span><b>Choose a video or audio file</b><small>Up to ' + L.max_minutes + " minutes · from your phone or computer</small>"
      + '<input type="file" accept="video/*,audio/*" hidden data-file></label><div class="vx-file" data-fi hidden></div></div>'
      + '<div data-box="url" hidden><input type="url" data-url placeholder="https://drive.google.com/file/d/…  or  https://…/video.mp4"><p class="vx-hint">A Google Drive or Dropbox link to your own video (shared with anyone who has the link), or a direct link to a video file.</p></div>'
      + '<h3 style="margin-top:14px">2. Languages</h3><div class="vx-row"><div><label class="l">Spoken in the video</label><select data-src>' + langOpts("", ["auto", "Find it automatically"]) + '</select></div>'
      + '<div><label class="l">Subtitles in</label><select data-to>' + langOpts("", ["", "Same as spoken"]) + "</select></div></div>"
      + '<button class="vx-btn g vx-go" data-go>Make subtitles</button>'
      + '<p class="vx-hint">⏱ Up to ' + L.max_minutes + " minutes per video · one video at a time · " + (L.unlimited ? "no daily limit for you" : L.per_day + " videos a day (" + L.used_today + " used)")
      + "<br>🗑️ Your video is deleted from our server " + L.keep_hours + " hours after upload. The subtitles stay " + L.keep_days + " days.<br>🤖 Subtitles are written by AI - mostly right, you can fix any line.</p></div>"
      + '<div class="vx-card vx-yt"><h3>▶️ YouTube videos</h3>YouTube does not allow downloading its videos, so paste-a-link does not work for YouTube, Facebook, Instagram, TikTok or Vimeo. '
      + "YouTube can translate its own subtitles:<ol><li>Open the video and tap <b>CC</b> (subtitles on).</li><li>Tap ⚙️ <b>Settings → Subtitles/CC → Auto-translate</b>.</li><li>Pick your language, for example Urdu.</li></ol>"
      + "Your own video from YouTube? Download it from YouTube Studio (Content → ⋮ → Download) and upload it here.</div>"
      + '<div class="vx-card"><h3>My videos</h3><div data-mine></div></div></div>';
    var $ = function(s){ return app.querySelector(s); };
    app.querySelectorAll("[data-m]").forEach(function(b){ b.onclick = function(){ mode = b.getAttribute("data-m"); app.querySelectorAll("[data-m]").forEach(function(x){ x.classList.toggle("on", x === b); });
      $("[data-box=file]").hidden = mode !== "file"; $("[data-box=url]").hidden = mode !== "url"; }; });
    $("[data-file]").onchange = function(){
      file = this.files[0]; var fi = $("[data-fi]"); if (!file){ fi.hidden = true; return; }
      fi.hidden = false; fi.innerHTML = "🎬 <b>" + esc(file.name) + "</b> · " + mb(file.size) + ' · <span data-len>checking length…</span>';
      lengthOf(file).then(function(d){ file._dur = d; var e = fi.querySelector("[data-len]");
        if (!d) e.textContent = "length unknown"; else if (d > L.max_minutes * 60 + 5){ e.innerHTML = '<b style="color:#B91C1C">' + tm(d) + " - too long (up to " + L.max_minutes + " minutes)</b>"; } else e.textContent = tm(d); });
    };
    $("[data-go]").onclick = function(){
      var bt = this, src = $("[data-src]").value, to = $("[data-to]").value;
      if (mode === "file"){
        if (!file){ toast("Choose a video first."); return; }
        if (file._dur > L.max_minutes * 60 + 5){ toast("The video is longer than " + L.max_minutes + " minutes."); return; }
        bt.disabled = true;
        api("new/", {name: file.name, size: file.size, duration: file._dur || 0, src: src, to: to}).then(function(j){
          bt.disabled = false; if (!j._ok){ toast(j.detail || "Could not start."); return; }
          LOCAL[j.id] = URL.createObjectURL(file); upload(j, file);
        });
      } else {
        var u = $("[data-url]").value.trim(); if (!/^https?:\/\//i.test(u)){ toast("Paste a full link that starts with https://"); return; }
        bt.disabled = true;
        api("new/", {url: u, src: src, to: to}).then(function(j){ bt.disabled = false; if (!j._ok){ toast(j.detail || "Could not start."); return; } open(j.id); });
      }
    };
    drawMine();
  }
  function lengthOf(f){
    return new Promise(function(ok){
      var v = D.createElement(f.type.indexOf("audio") === 0 ? "audio" : "video"), u = URL.createObjectURL(f), t = setTimeout(function(){ ok(0); }, 15000);
      v.preload = "metadata"; v.onloadedmetadata = function(){ clearTimeout(t); var d = v.duration; URL.revokeObjectURL(u); ok(isFinite(d) ? d : 0); };
      v.onerror = function(){ clearTimeout(t); ok(0); }; v.src = u;
    });
  }
  function drawMine(){
    var box = app.querySelector("[data-mine]"); if (!box) return;
    var J = INFO.jobs || [];
    box.innerHTML = J.length ? J.map(function(j){
      var st = j.status === "ready" ? '<span class="vx-badge ok">Ready</span>' : j.status === "failed" ? '<span class="vx-badge bad">Failed</span>' : '<span class="vx-badge">' + esc(j.status_label) + (j.progress ? " " + j.progress + "%" : "") + "</span>";
      return '<div class="vx-job"><div class="t"><b>' + esc(j.title) + "</b><small>" + (j.duration ? tm(j.duration) + " · " : "") + (j.lang_name ? esc(j.lang_name) + " · " : "") + new Date(j.created).toLocaleString() + (j.video ? " · video kept " + left(j.video_left) : "") + "</small></div>" + st
        + ' <button class="vx-btn o s" data-open="' + j.id + '">Open</button></div>'; }).join("") : '<p class="vx-hint">Your videos will show here.</p>';
    box.querySelectorAll("[data-open]").forEach(function(b){ b.onclick = function(){ open(+b.getAttribute("data-open")); }; });
  }

  /* ---------------------------------------------------------------- upload in pieces */
  function upload(j, file){
    busyUp = true; var lock = null;
    try { if (navigator.wakeLock) navigator.wakeLock.request("screen").then(function(l){ lock = l; }).catch(function(){}); } catch (e) {}
    try { history.pushState(null, "", "/video-translate?id=" + j.id); } catch (e) {}
    app.innerHTML = '<div class="vx"><div class="vx-card"><h3>⬆️ Uploading ' + esc(file.name) + '</h3><div class="vx-bar"><i data-p></i></div><p class="vx-hint" data-t>Starting…</p>'
      + '<p class="vx-hint">Keep this page open until the upload finishes. Big video? Wi-Fi is faster.</p><div class="vx-acts"><button class="vx-btn r s" data-stop>Cancel</button></div></div></div>';
    var n = Math.ceil(file.size / j.chunk_size), i = j.chunks || 0, stop = false, t0 = Date.now();
    app.querySelector("[data-stop]").onclick = function(){ stop = true; api(j.id + "/delete/", {}).then(function(){ busyUp = false; boot(); }); };
    (function next(tries){
      if (stop) return;
      if (i >= n){
        busyUp = false; if (lock) try { lock.release(); } catch (e) {}
        api(j.id + "/done/", {}).then(function(x){ if (!x._ok){ toast(x.detail || "Upload problem."); boot(); return; } open(j.id); });
        return;
      }
      var fd = new FormData(); fd.append("i", i); fd.append("c", file.slice(i * j.chunk_size, Math.min(file.size, (i + 1) * j.chunk_size)), "c");
      api(j.id + "/chunk/", null, fd).then(function(r){
        if (!r._ok){
          if (tries < 5 && r._s !== 404 && r._s !== 409 && r._s !== 400){ var w = app.querySelector("[data-t]"); if (w) w.textContent = "Network problem - trying again…"; setTimeout(function(){ next(tries + 1); }, 2000 * (tries + 1)); return; }
          busyUp = false; toast(r.detail || "The upload stopped. Try again."); boot(); return;
        }
        i = r.chunks; var done = Math.min(file.size, i * j.chunk_size), sp = done / Math.max(1, (Date.now() - t0) / 1000);
        var p = app.querySelector("[data-p]"), t = app.querySelector("[data-t]");
        if (p) p.style.width = (done * 100 / file.size).toFixed(1) + "%";
        if (t) t.textContent = mb(done) + " of " + mb(file.size) + " · " + Math.round(done * 100 / file.size) + "%" + (sp > 0 && i < n ? " · about " + left((file.size - done) / sp) + " left" : "");
        next(0);
      });
    })(0);
  }
  window.addEventListener("beforeunload", function(e){ if (busyUp){ e.preventDefault(); e.returnValue = ""; } });

  /* ---------------------------------------------------------------- one video */
  var view = {lang: null, j: null};
  function open(id){
    try { if (location.search.indexOf("id=" + id) < 0) history.pushState(null, "", "/video-translate?id=" + id); } catch (e) {}
    CUR = id; view.lang = null;
    app.innerHTML = '<div class="vx"><p class="vx-hint">Loading…</p></div>';
    load();
  }
  function load(){
    clearTimeout(pollT);
    var id = CUR; if (!id) return;
    api(id + "/").then(function(j){
      if (CUR !== id) return;
      if (!j._ok){ app.innerHTML = '<div class="vx"><div class="vx-card"><p>' + esc(j.detail || "Not found.") + '</p><a class="vx-btn" href="/video-translate">Back</a></div></div>'; return; }
      view.j = j;
      if (j.status !== "ready") return working(j);
      player(j);
      if (j.tracks.some(function(t){ return t.status === "queued" || t.status === "working"; })) pollT = setTimeout(load, 3000);
    });
  }
  function working(j){
    var msg = {uploading: "The upload did not finish. Delete it and start again.", downloading: "Downloading the video from your link…", queued: "Waiting for its turn…",
      working: "Listening to the video and writing subtitles… (" + j.progress + "%)", failed: j.error || "Something went wrong."}[j.status] || j.status_label;
    app.innerHTML = '<div class="vx"><div class="vx-card"><h3>' + (j.status === "failed" ? "⚠️ " : "⏳ ") + esc(j.title) + "</h3>"
      + (j.status === "failed" ? "" : '<div class="vx-bar"><i style="width:' + (j.status === "downloading" ? (j.size ? j.got * 100 / j.size : 5) : j.status === "working" ? Math.max(3, j.progress) : 2) + '%"></i></div>')
      + '<p style="margin:6px 0 0">' + esc(msg) + "</p>"
      + (j.status === "working" || j.status === "queued" ? '<p class="vx-hint">A ' + (j.duration ? tm(j.duration) : "") + " video takes a few minutes. You can close this page - you get a notification when it is ready.</p>" : "")
      + '<div class="vx-acts"><a class="vx-btn o s" href="/video-translate">← My videos</a><button class="vx-btn r s" data-del>Delete</button></div></div></div>';
    app.querySelector("[data-del]").onclick = function(){ del(j.id); };
    if (j.status !== "failed" && j.status !== "uploading") pollT = setTimeout(load, 3000);
  }
  function del(id){
    if (!confirm("Delete this video and its subtitles?")) return;
    api(id + "/delete/", {}).then(function(){ toast("Deleted"); boot(); });
  }
  function segsFor(j, lang){
    if (lang === j.lang) return j.segments;
    var t = j.tracks.filter(function(x){ return x.lang === lang; })[0]; return t && t.status === "ready" ? t.segments : null;
  }
  function vtt(segs){
    var f = function(s){ s = Math.max(0, s); var h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = (s % 60).toFixed(3); return ("0" + h).slice(-2) + ":" + ("0" + m).slice(-2) + ":" + ("0" + x).slice(-6); };
    return "WEBVTT\n\n" + segs.map(function(x, i){ return (i + 1) + "\n" + f(x.s) + " --> " + f(x.e) + "\n" + x.t + "\n"; }).join("\n");
  }
  function player(j){
    var lang = view.lang || (j.tracks.filter(function(t){ return t.status === "ready"; }).slice(-1)[0] || {}).lang || j.lang;
    if (!segsFor(j, lang)) lang = j.lang;
    view.lang = lang;
    var src = LOCAL[j.id] || (j.video ? API + j.id + "/video/" : "");
    var keep = D.querySelector(".vx-player video"), same = keep && keep.getAttribute("data-for") === String(j.id) && keep.getAttribute("data-src") === src;
    var at = same ? keep.currentTime : 0, playing = same && !keep.paused;
    var segs = segsFor(j, lang), rtl = RTL.indexOf(lang) >= 0;
    var chips = '<button data-l="' + j.lang + '"' + (lang === j.lang ? ' class="on"' : "") + ">" + esc(j.lang_name) + " (spoken)</button>" + j.tracks.map(function(t){
      return '<button data-l="' + t.lang + '"' + (t.lang === lang ? ' class="on"' : "") + (t.status !== "ready" ? " disabled" : "") + ">" + esc(t.name) + (t.status === "ready" ? "" : t.status === "failed" ? " ⚠️" : " " + t.progress + "%…") + "</button>"; }).join("");
    app.innerHTML = '<div class="vx"><div class="vx-acts" style="margin:0"><a class="vx-btn o s" href="/video-translate">← My videos</a></div>'
      + '<h1 style="font-size:20px;margin:10px 0 0;word-break:break-word">' + esc(j.title) + '</h1><p class="vx-hint" style="margin-top:2px">' + tm(j.duration) + " · " + j.lines + " lines · spoken in " + esc(j.lang_name) + "</p>"
      + (src ? '<div class="vx-player"><video controls playsinline preload="metadata" data-for="' + j.id + '" data-src="' + esc(src) + '"></video></div>'
             : '<div class="vx-note">🗑️ The video was deleted from our server (videos are kept ' + INFO.limits.keep_hours + ' hours). The subtitles are still here. <label class="vx-btn o s" style="margin-top:6px">📁 Open the video from your phone to watch it with subtitles<input type="file" accept="video/*,audio/*" hidden data-again></label></div>')
      + (j.video && !LOCAL[j.id] ? '<p class="vx-hint">🗑️ This video is deleted from our server in ' + left(j.video_left) + ". Download the subtitles to keep them with your video.</p>" : "")
      + '<div class="vx-langs">' + chips + '<select data-add><option value="">＋ Translate to…</option>' + INFO.langs.filter(function(l){ return l.code !== j.lang && !j.tracks.some(function(t){ return t.lang === l.code; }); }).map(function(l){ return '<option value="' + l.code + '">' + esc(l.name) + (l.native !== l.name ? " · " + esc(l.native) : "") + "</option>"; }).join("") + "</select></div>"
      + '<div class="vx-acts"><button class="vx-btn s" data-copy>📋 Copy text</button><a class="vx-btn o s" href="' + API + j.id + "/sub/?fmt=srt&dl=1&lang=" + lang + '">⬇️ .srt</a><a class="vx-btn o s" href="' + API + j.id + "/sub/?fmt=vtt&dl=1&lang=" + lang + '">⬇️ .vtt</a><a class="vx-btn o s" href="' + API + j.id + "/sub/?fmt=txt&dl=1&lang=" + lang + '">⬇️ .txt</a><button class="vx-btn r s" data-del>Delete</button></div>'
      + '<p class="vx-hint">.srt and .vtt files can be added to your video on YouTube (Subtitles → Upload file) and Facebook. Tap a line to jump there; ✏️ to fix it.</p>'
      + '<div class="vx-lines" data-lines>' + segs.map(function(x, i){ return '<div class="vx-ln' + (rtl ? " rtl" : "") + '" data-i="' + i + '"><small>' + tm(x.s) + "</small><p>" + esc(x.t) + '</p><button class="ed" data-ed="' + i + '" aria-label="Fix this line">✏️</button></div>'; }).join("") + "</div></div>";
    var v = app.querySelector(".vx-player video");
    if (v){
      v.src = src; var tr = D.createElement("track"); tr.kind = "subtitles"; tr.srclang = lang; tr.label = nameOf(lang); tr.default = true;
      tr.src = URL.createObjectURL(new Blob([vtt(segs)], {type: "text/vtt"})); v.appendChild(tr);
      v.addEventListener("loadedmetadata", function(){ try { v.textTracks[0].mode = "showing"; } catch (e) {} if (at) v.currentTime = at; if (playing) v.play().catch(function(){}); });
      v.addEventListener("error", function(){ if (!LOCAL[j.id]) { view.j.video = false; player(view.j); } });
      var lastOn = -1;
      v.addEventListener("timeupdate", function(){
        var t = v.currentTime, k = -1; for (var i = 0; i < segs.length; i++){ if (segs[i].s <= t && t < segs[i].e + 0.3){ k = i; break; } }
        if (k === lastOn) return; lastOn = k;
        app.querySelectorAll(".vx-ln.on").forEach(function(e){ e.classList.remove("on"); });
        var el = app.querySelector('.vx-ln[data-i="' + k + '"]'); if (el){ el.classList.add("on"); var box = app.querySelector("[data-lines]"); if (box) box.scrollTop = el.offsetTop - box.offsetTop - 60; }
      });
    }
    var again = app.querySelector("[data-again]"); if (again) again.onchange = function(){ if (this.files[0]){ LOCAL[j.id] = URL.createObjectURL(this.files[0]); player(view.j); } };
    app.querySelectorAll("[data-l]").forEach(function(b){ b.onclick = function(){ view.lang = b.getAttribute("data-l"); player(view.j); }; });
    app.querySelector("[data-add]").onchange = function(){
      var to = this.value; if (!to) return;
      api(j.id + "/translate/", {lang: to}).then(function(x){ if (!x._ok){ toast(x.detail || "Could not."); return; } view.j = x; view.lang = j.lang; player(x); toast("Translating to " + nameOf(to) + "…"); clearTimeout(pollT); pollT = setTimeout(load, 3000); });
    };
    app.querySelector("[data-copy]").onclick = function(){
      var text = segs.map(function(x){ return x.t; }).join("\n");
      (navigator.clipboard ? navigator.clipboard.writeText(text) : Promise.reject()).then(function(){ toast("Copied ✔"); }, function(){
        var ta = D.createElement("textarea"); ta.value = text; B.appendChild(ta); ta.select(); try { D.execCommand("copy"); toast("Copied ✔"); } catch (e) {} ta.remove(); });
    };
    app.querySelector("[data-del]").onclick = function(){ del(j.id); };
    app.querySelector("[data-lines]").addEventListener("click", function(e){
      var ed = e.target.closest("[data-ed]");
      if (ed){
        e.stopPropagation(); var i = +ed.getAttribute("data-ed"), row = ed.closest(".vx-ln");
        row.innerHTML = '<small>' + tm(segs[i].s) + '</small><div style="flex:1"><textarea ' + (rtl ? 'dir="rtl"' : "") + ">" + esc(segs[i].t) + '</textarea><div class="vx-acts" style="margin-top:6px"><button class="vx-btn g s" data-sv>Save</button><button class="vx-btn o s" data-cx>Cancel</button></div></div>';
        row.querySelector("textarea").focus();
        row.querySelector("[data-cx]").onclick = function(ev){ ev.stopPropagation(); player(view.j); };
        row.querySelector("[data-sv]").onclick = function(ev){
          ev.stopPropagation(); var t = row.querySelector("textarea").value.trim();
          api(j.id + "/edit/", {lang: lang, i: i, t: t}).then(function(x){ if (!x._ok){ toast(x.detail || "Could not save."); return; } segs[i].t = t; toast("Saved ✔"); player(view.j); });
        };
        return;
      }
      var row2 = e.target.closest("[data-i]"); if (!row2 || e.target.closest("textarea,button")) return;
      var vv = app.querySelector(".vx-player video"); if (vv){ vv.currentTime = segs[+row2.getAttribute("data-i")].s + 0.01; vv.play().catch(function(){}); }
    });
  }

  /* ---------------------------------------------------------------- start */
  function boot(){
    clearTimeout(pollT);
    api("mine/").then(function(d){
      if (d._s === 401 || d._s === 403){
        app.innerHTML = '<div class="vx"><div class="vx-hero"><h1>🎬 Video Translate</h1><div class="vx-ur">ویڈیو کا ترجمہ — سب ٹائٹل کسی بھی زبان میں</div><p>Subtitles and a transcript for your video, in any language. Free for members.</p></div>'
          + '<div class="vx-card"><p>Please sign in to translate your videos.</p><a class="vx-btn g" href="/login?next=/video-translate">Sign in or create a free account</a></div></div>';
        return;
      }
      INFO = d;
      var id = +(new URLSearchParams(location.search).get("id") || 0);
      if (id) open(id); else home();
    });
  }
  window.addEventListener("popstate", function(){ if (!busyUp) boot(); });
  boot();
})();
