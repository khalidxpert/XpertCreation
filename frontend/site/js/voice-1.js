/* Voice messages for XpertCreation chats and groups: a recorder (tap the mic, then Send or Cancel) and a
   small player (play/pause, progress, length, speed). One voice note plays at a time. */
(function(){
  "use strict";
  var MAX = 180, css = false, playing = null;
  function esc(s){ return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function fmt(s){ s = Math.max(0, Math.round(s || 0)); return Math.floor(s / 60) + ":" + ("0" + (s % 60)).slice(-2); }
  function style(){
    if (css) return; css = true;
    var st = document.createElement("style");
    st.textContent = ".xvn{display:flex;align-items:center;gap:8px;min-width:200px;max-width:280px;padding:4px 0}"
      + ".xvp{width:36px;height:36px;flex:0 0 36px;border-radius:50%;border:0;background:rgba(13,20,36,.1);color:inherit;font-size:14px;cursor:pointer}"
      + ".mine .xvp,.me .xvp{background:rgba(255,255,255,.25)}"
      + ".xvb{flex:1;height:4px;border-radius:4px;background:rgba(13,20,36,.15);position:relative;cursor:pointer}.mine .xvb,.me .xvb{background:rgba(255,255,255,.35)}"
      + ".xvb i{position:absolute;left:0;top:0;bottom:0;width:0;border-radius:4px;background:currentColor}"
      + ".xvt{font-size:12px;opacity:.8;min-width:32px;text-align:right}.xvs{border:0;background:transparent;color:inherit;font-size:11.5px;font-weight:800;cursor:pointer;opacity:.8;padding:4px}"
      + ".xvrec{display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:14px;background:var(--card,#fff);border:1px solid var(--line,#E4E8F2)}"
      + ".xvrec .dot{width:10px;height:10px;border-radius:50%;background:#DC2626;animation:xvblink 1s infinite}.xvrec .t{flex:1;font-weight:700}"
      + ".xvrec button{border:0;border-radius:12px;padding:9px 14px;font:inherit;font-weight:800;cursor:pointer}.xvrec .x{background:var(--paper,#F6F7FB);color:var(--ink,#0D1424)}.xvrec .ok{background:var(--brand,#1B4DFF);color:#fff}"
      + "@keyframes xvblink{50%{opacity:.25}}";
    document.head.appendChild(st);
  }
  function html(v){
    style();
    return '<div class="xvn" data-src="' + esc(v.url) + '" data-secs="' + (v.secs || 0) + '"><button class="xvp" type="button" aria-label="Play">\u25B6</button>'
      + '<div class="xvb"><i></i></div><span class="xvt">' + fmt(v.secs) + '</span><button class="xvs" type="button">1\u00d7</button></div>';
  }
  function stop(){
    if (!playing) return;
    playing.audio.pause();
    playing.el.querySelector(".xvp").textContent = "\u25B6";
    playing = null;
  }
  document.addEventListener("click", function(e){
    var sp = e.target.closest && e.target.closest(".xvs");
    if (sp){
      var r = {"1\u00d7": 1.5, "1.5\u00d7": 2, "2\u00d7": 1}[sp.textContent] || 1;
      sp.textContent = r + "\u00d7";
      if (playing && playing.el.contains(sp)) playing.audio.playbackRate = r;
      e.stopPropagation(); return;
    }
    var bar = e.target.closest && e.target.closest(".xvb");
    if (bar && playing && playing.el.contains(bar) && playing.audio.duration){
      var rc = bar.getBoundingClientRect();
      playing.audio.currentTime = playing.audio.duration * Math.min(1, Math.max(0, (e.clientX - rc.left) / rc.width)); e.stopPropagation(); return;
    }
    var b = e.target.closest && e.target.closest(".xvp");
    if (!b) return;
    e.stopPropagation();
    var el = b.closest(".xvn");
    if (playing && playing.el === el){ if (playing.audio.paused){ playing.audio.play(); b.textContent = "\u275A\u275A"; } else { playing.audio.pause(); b.textContent = "\u25B6"; } return; }
    stop();
    var a = new Audio(el.getAttribute("data-src")), fill = el.querySelector(".xvb i"), t = el.querySelector(".xvt"), secs = +el.getAttribute("data-secs") || 0;
    a.playbackRate = parseFloat(el.querySelector(".xvs").textContent) || 1;
    playing = {el: el, audio: a};
    a.addEventListener("timeupdate", function(){
      var d = isFinite(a.duration) && a.duration > 0 ? a.duration : secs;
      if (d) fill.style.width = Math.min(100, a.currentTime / d * 100) + "%";
      t.textContent = fmt(a.currentTime);
    });
    a.addEventListener("ended", function(){ fill.style.width = "0"; t.textContent = fmt(secs); b.textContent = "\u25B6"; playing = null; });
    a.addEventListener("error", function(){ b.textContent = "\u25B6"; playing = null; alert("This voice message could not be played."); });
    b.textContent = "\u275A\u275A";
    a.play().catch(function(){});
  }, true);

  /* recorder({mic: button id, box: id of the typing row to swap out, upload: function(FormData)}) */
  function recorder(o){
    style();
    var rec = null, chunks = [], started = 0, tick = null, stream = null, bar = null, cancelled = false;
    function pickType(){
      var T = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"];
      for (var i = 0; i < T.length; i++) if (window.MediaRecorder && MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(T[i])) return T[i];
      return "";
    }
    function done(){
      clearInterval(tick);
      if (stream) stream.getTracks().forEach(function(t){ t.stop(); });
      if (bar) bar.remove();
      var box = document.getElementById(o.box); if (box) box.style.display = "";
      rec = null; bar = null; stream = null;
    }
    function finish(send){
      if (!rec) return;
      cancelled = !send;
      if (rec.state !== "inactive") rec.stop(); else done();
    }
    function start(){
      if (rec) return;
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder){ alert("This browser can't record voice messages."); return; }
      navigator.mediaDevices.getUserMedia({audio: true}).then(function(s){
        stream = s; chunks = []; cancelled = false;
        var type = pickType();
        try { rec = new MediaRecorder(s, type ? {mimeType: type, audioBitsPerSecond: 32000} : {audioBitsPerSecond: 32000}); }
        catch (err) { rec = new MediaRecorder(s); }
        rec.ondataavailable = function(ev){ if (ev.data && ev.data.size) chunks.push(ev.data); };
        rec.onstop = function(){
          var secs = Math.round((Date.now() - started) / 1000), mt = (rec && rec.mimeType) || type || "audio/webm";
          done();
          if (cancelled || secs < 1 || !chunks.length) return;
          var blob = new Blob(chunks, {type: mt.split(";")[0]}), ext = /mp4/.test(mt) ? "m4a" : /ogg/.test(mt) ? "ogg" : "webm";
          var fd = new FormData(); fd.append("voice", blob, "voice." + ext); fd.append("secs", String(Math.min(secs, MAX)));
          o.upload(fd);
        };
        var box = document.getElementById(o.box);
        bar = document.createElement("div"); bar.className = "xvrec";
        bar.innerHTML = '<span class="dot"></span><span class="t">0:00</span><button class="x" type="button">Cancel</button><button class="ok" type="button">Send \u27A4</button>';
        bar.querySelector(".x").onclick = function(){ finish(false); };
        bar.querySelector(".ok").onclick = function(){ finish(true); };
        if (box){ box.parentNode.insertBefore(bar, box); box.style.display = "none"; }
        started = Date.now(); rec.start(1000);
        tick = setInterval(function(){
          var s = Math.round((Date.now() - started) / 1000);
          if (bar) bar.querySelector(".t").textContent = fmt(s) + (s >= MAX - 10 ? "  (max " + fmt(MAX) + ")" : "");
          if (s >= MAX) finish(true);
        }, 250);
      }).catch(function(){ alert("Allow the microphone for xpertcreation.com to record voice messages (browser or app settings)."); });
    }
    document.addEventListener("click", function(e){ if (e.target.closest && e.target.closest("#" + o.mic)){ e.preventDefault(); start(); } });
  }
  window.XCVoice = {html: html, recorder: recorder, fmt: fmt};
})();
