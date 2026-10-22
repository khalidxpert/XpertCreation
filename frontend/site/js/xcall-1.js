/* XpertChat calls + XpertMeet (xcall-1.js)
   Voice and video calls straight between phones (WebRTC). The server rings people and passes set-up messages.
   On chat pages: call buttons, ringing screen for incoming calls, join button for group calls.
   On /call: answer a call from a notification, or start / join an XpertMeet meeting. */
(function(){
  "use strict";
  if (window.XCCALL) return;
  var D = document, B = D.body || D.documentElement;
  var PAGE = /^\/call/.test(location.pathname) ? "call" : /^\/group\//.test(location.pathname) ? "group" : /^\/chat/.test(location.pathname) ? "chat" : "other";
  function $(id){ return D.getElementById(id); }
  function esc(s){ return String(s == null ? "" : s).replace(/[&<>"']/g, function(c){ return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]; }); }
  function ck(n){ var m = D.cookie.match(new RegExp("(?:^|; )" + n + "=([^;]*)")); return m ? decodeURIComponent(m[1]) : ""; }
  function api(p, body){
    var o = {method: body === undefined ? "GET" : "POST", credentials: "same-origin", headers: {"Accept": "application/json"}};
    if (body !== undefined){ o.headers["Content-Type"] = "application/json"; o.headers["X-CSRFToken"] = ck("xc_csrf") || ck("csrftoken"); o.body = JSON.stringify(body); }
    return fetch("/api/calls/" + p, o).then(function(r){ return r.text().then(function(t){ var d = {}; try { d = t ? JSON.parse(t) : {}; } catch (e) {} if (!r.ok){ var er = new Error(d.detail || ("Error " + r.status)); er.status = r.status; throw er; } return d; }); });
  }
  var ICON = {
    phone: '<svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor"><path d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.25 11.4 11.4 0 0 0 3.6.57 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.45.57 3.6a1 1 0 0 1-.25 1z"/></svg>',
    video: '<svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor"><path d="M17 10.5V7a1 1 0 0 0-1-1H4a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-3.5l4 4v-11z"/></svg>',
    mic: '<svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.9V21h2v-3.1A7 7 0 0 0 19 11z"/></svg>',
    micoff: '<svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M19 11h-2a5 5 0 0 1-.6 2.4l1.5 1.5A7 7 0 0 0 19 11zM15 11V5a3 3 0 0 0-5.9-.8L15 10.1zM4.3 3 3 4.3l6 6V11a3 3 0 0 0 4.3 2.7l1.6 1.6A5 5 0 0 1 7 11H5a7 7 0 0 0 6 6.9V21h2v-3.1a6.9 6.9 0 0 0 3.4-1.3l3.3 3.3 1.3-1.3z"/></svg>',
    cam: '<svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M17 10.5V7a1 1 0 0 0-1-1H4a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-3.5l4 4v-11z"/></svg>',
    camoff: '<svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M21 6.5l-4 4V7a1 1 0 0 0-1-1H9.8L21 17.2zM3.3 2 2 3.3 4.7 6H4a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h12a1 1 0 0 0 .6-.2l3.1 3.2 1.3-1.3z"/></svg>',
    flip: '<svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M20 5h-3.2L15 3H9L7.2 5H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2zm-8 13a5 5 0 0 1-4.6-3H9l-2.5-2.5L4 15h1.3A7 7 0 0 0 12 20zm0-10a5 5 0 0 1 4.6 3H15l2.5 2.5L20 13h-1.3A7 7 0 0 0 12 8z"/></svg>',
    screen: '<svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M20 4H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h6v2H8v2h8v-2h-2v-2h6a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zm-8 3 4 4h-3v4h-2v-4H8z"/></svg>',
    end: '<svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor"><path d="M12 9c-1.6 0-3.15.25-4.6.72v3.1a1 1 0 0 1-.56.9 11.5 11.5 0 0 0-2.66 1.85 1 1 0 0 1-1.4 0L.3 13.1a1 1 0 0 1 0-1.4A16.9 16.9 0 0 1 12 7c4.5 0 8.6 1.75 11.7 4.7a1 1 0 0 1 0 1.4l-2.5 2.5a1 1 0 0 1-1.4 0 11.3 11.3 0 0 0-2.66-1.86 1 1 0 0 1-.56-.9v-3.1A15 15 0 0 0 12 9z"/></svg>',
    link: '<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M10.6 13.4a1 1 0 0 1 0-1.4l3-3a1 1 0 1 1 1.4 1.4l-3 3a1 1 0 0 1-1.4 0zm-2.1 4.4a3 3 0 0 1-2.1-5.1l2-2a1 1 0 1 0-1.4-1.4l-2 2a5 5 0 0 0 7.1 7.1l2-2a1 1 0 0 0-1.4-1.4l-2 2a3 3 0 0 1-2.2.8zm9.7-13.7a5 5 0 0 0-7.1 0l-2 2a1 1 0 1 0 1.4 1.4l2-2a3 3 0 0 1 4.3 4.2l-2 2a1 1 0 0 0 1.4 1.4l2-2a5 5 0 0 0 0-7z"/></svg>'
  };

  /* ------------------------------------------------------------ styles */
  var st = D.createElement("style");
  st.textContent = ""
   + ".xkbar{display:inline-flex;gap:4px;margin-left:auto}.xkbtn{width:40px;height:40px;border-radius:50%;border:0;background:transparent;color:inherit;display:inline-flex;align-items:center;justify-content:center;cursor:pointer}.xkbtn:hover{background:rgba(127,127,127,.15)}"
   + ".xkhead{display:flex;align-items:center;gap:6px}"
   + ".xkfloat{position:fixed;top:8px;right:8px;z-index:60;display:flex;gap:4px;background:var(--card,#fff);border-radius:24px;box-shadow:0 2px 10px rgba(0,0,0,.15);padding:2px}"
   + ".xkjoin{position:sticky;top:0;z-index:50;margin:6px 0;padding:10px 14px;border-radius:12px;background:#0f9d58;color:#fff;display:flex;align-items:center;gap:10px;font-weight:600;cursor:pointer;border:0;width:100%;font:inherit}"
   + ".xkov{position:fixed;inset:0;z-index:2147483000;background:#0b1220;color:#fff;display:flex;flex-direction:column;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}"
   + ".xktop{padding:calc(14px + env(safe-area-inset-top)) 16px 8px;text-align:center}.xktop b{display:block;font-size:1.25rem}.xktop span{opacity:.75;font-size:.95rem}"
   + ".xkstage{flex:1;position:relative;display:grid;gap:6px;padding:6px;min-height:0}.xkstage.n1{grid-template-columns:1fr}.xkstage.n2{grid-template-columns:1fr}.xkstage.n3,.xkstage.n4{grid-template-columns:1fr 1fr}"
   + "@media(min-width:800px){.xkstage.n2{grid-template-columns:1fr 1fr}}"
   + ".xktile{position:relative;background:#16213a;border-radius:14px;overflow:hidden;display:flex;align-items:center;justify-content:center;min-height:0}"
   + ".xktile video{width:100%;height:100%;object-fit:cover;background:#000}.xktile.scr video{object-fit:contain}.xktile .xkav{width:96px;height:96px;border-radius:50%;background:#2a3a5e center/cover;display:flex;align-items:center;justify-content:center;font-size:2.4rem;font-weight:700}"
   + ".xktile .xknm{position:absolute;left:10px;bottom:8px;font-size:.85rem;background:rgba(0,0,0,.45);padding:2px 8px;border-radius:10px}"
   + ".xkself{position:absolute;right:12px;bottom:12px;width:28vw;max-width:170px;aspect-ratio:3/4;border-radius:12px;overflow:hidden;background:#000;box-shadow:0 4px 18px rgba(0,0,0,.5);z-index:3}.xkself video{width:100%;height:100%;object-fit:cover;transform:scaleX(-1)}.xkself.scr video{transform:none;object-fit:contain}"
   + ".xkctl{display:flex;justify-content:center;gap:14px;flex-wrap:wrap;padding:14px 12px calc(18px + env(safe-area-inset-bottom))}"
   + ".xkc{width:56px;height:56px;border-radius:50%;border:0;background:rgba(255,255,255,.16);color:#fff;display:flex;align-items:center;justify-content:center;cursor:pointer}.xkc.off{background:#fff;color:#0b1220}.xkc.red{background:#e53935}.xkc.green{background:#0f9d58}.xkc:disabled{opacity:.4}"
   + ".xkring .xkc{width:66px;height:66px}.xkring .xkstage{align-content:center;justify-items:center}"
   + ".xklbl{font-size:.75rem;text-align:center;opacity:.8;margin-top:4px}.xkcw{display:flex;flex-direction:column;align-items:center}"
   + ".xkbig{width:120px;height:120px;border-radius:50%;background:#2a3a5e center/cover;display:flex;align-items:center;justify-content:center;font-size:3rem;font-weight:700;animation:xkp 1.6s infinite}"
   + "@keyframes xkp{0%{box-shadow:0 0 0 0 rgba(15,157,88,.6)}70%{box-shadow:0 0 0 26px rgba(15,157,88,0)}100%{box-shadow:0 0 0 0 rgba(15,157,88,0)}}"
   + ".xkmsg{position:absolute;left:50%;top:14px;transform:translateX(-50%);background:rgba(0,0,0,.6);padding:6px 12px;border-radius:14px;font-size:.9rem;z-index:4;max-width:90%;text-align:center}"
   + ".xkshare{margin:8px auto 0;display:flex;gap:6px;align-items:center;justify-content:center;flex-wrap:wrap}.xkshare code{background:rgba(255,255,255,.12);padding:6px 10px;border-radius:8px;font-size:.9rem;word-break:break-all}"
   + ".xkpill{border:0;border-radius:18px;padding:7px 14px;background:#fff;color:#0b1220;font:inherit;font-weight:600;cursor:pointer}"
   + ".xklobby{max-width:460px;margin:auto;padding:24px 18px;text-align:center}.xklobby h1{font-size:1.6rem;margin:10px 0 4px}.xklobby p{opacity:.8}.xklobby input{width:100%;box-sizing:border-box;padding:12px;border-radius:12px;border:1px solid #33415f;background:#111a2e;color:#fff;font:inherit;margin:8px 0}"
   + ".xklobby .row{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin-top:10px}.xklobby .xkpill.g{background:#0f9d58;color:#fff}.xklobby .xkpill.o{background:transparent;color:#fff;border:1px solid #fff}"
   + ".xkinv{margin:14px 0;padding:12px;border-radius:14px;background:rgba(255,255,255,.07);text-align:left}.xktz{display:grid;grid-template-columns:1fr 1fr;gap:4px 10px;font-size:.86rem;margin:8px 0}"
   + ".xklobby input[type=datetime-local]{color-scheme:dark}.xklobby label{display:block;text-align:left;font-size:.9rem;opacity:.85;margin-top:8px}"
   + ".xklobby label.xksr,.xksr{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:12px 0;border-bottom:1px solid rgba(255,255,255,.1)}.xksr input{width:22px;height:22px}"
   + ".xkpk{display:flex;gap:6px;flex-wrap:wrap;padding:8px 0}.xkpk .xkpill{font-size:.85rem;padding:5px 10px}"
   + ".xklobby .er{color:#ff8a80;min-height:1.2em}.xkur{font-family:'Noto Nastaliq Urdu',serif;opacity:.8;display:block;margin-top:2px}";
  D.head.appendChild(st);

  /* ------------------------------------------------------------ sounds: settings, message tones, ringtones (generated, no files) */
  var SND = {msg: true, msgTone: 0, grp: true, ring: true, ringTone: 0, vib: true};
  try { var sv = JSON.parse(localStorage.getItem("xc_sound") || "{}"); for (var k in sv) if (k in SND) SND[k] = sv[k]; } catch (e) {}
  function saveSnd(){ try { localStorage.setItem("xc_sound", JSON.stringify(SND)); } catch (e) {} }
  var ring = { ctx: null, t: null, on: false };
  function actx(){
    try { var C = window.AudioContext || window.webkitAudioContext; if (!C) return null; ring.ctx = ring.ctx || new C(); if (ring.ctx.state === "suspended") ring.ctx.resume().catch(function(){}); return ring.ctx; } catch (e) { return null; }
  }
  // browsers only allow sound after the person has tapped the page once
  ["pointerdown", "keydown", "touchstart"].forEach(function(ev){ D.addEventListener(ev, function u(){ actx(); D.removeEventListener(ev, u, true); }, true); });
  function note(c, f, start, len, vol, type){
    var o = c.createOscillator(), g = c.createGain(), t = c.currentTime + start;
    o.type = type || "sine"; o.frequency.setValueAtTime(f, t);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + 0.015); g.gain.exponentialRampToValueAtTime(0.0001, t + len);
    o.connect(g); g.connect(c.destination); o.start(t); o.stop(t + len + 0.05);
  }
  var TONES = [["Pop", function(c, v){ note(c, 880, 0, 0.12, v); note(c, 1320, 0.07, 0.16, v * 0.8); }],
               ["Chime", function(c, v){ note(c, 1046, 0, 0.35, v * 0.8, "triangle"); note(c, 1568, 0.12, 0.45, v * 0.6, "triangle"); }],
               ["Ding", function(c, v){ note(c, 1760, 0, 0.5, v * 0.7); note(c, 2637, 0, 0.3, v * 0.25); }]];
  var RINGS = [["Classic", function(c){ for (var i = 0; i < 2; i++){ note(c, 480, i * 0.45, 0.4, 0.13); note(c, 620, i * 0.45, 0.4, 0.1); } }],
               ["Marimba", function(c){ [784, 988, 1175, 988, 784, 988].forEach(function(f, i){ note(c, f, i * 0.16, 0.25, 0.14, "triangle"); }); }],
               ["Soft bells", function(c){ [1046, 1318, 1568, 2093].forEach(function(f, i){ note(c, f, i * 0.22, 0.6, 0.09); }); }]];
  function tone(kind, force){
    if (!force && (kind === "grp" ? !(SND.msg && SND.grp) : !SND.msg)) return;
    var c = actx(); if (!c) return;
    try { TONES[SND.msgTone % TONES.length][1](c, kind === "open" ? 0.05 : 0.09); } catch (e) {}
    if (SND.vib && kind !== "open" && !force){ try { navigator.vibrate && navigator.vibrate(120); } catch (e) {} }
  }
  function soundsPanel(){
    var old = D.querySelector(".xksnd"); if (old) old.remove();
    var ov = D.createElement("div"); ov.className = "xkov xksnd";
    var row = function(k, label, ur){ return '<label class="xksr"><span>' + label + '<span class="xkur" dir="rtl" lang="ur">' + ur + '</span></span><input type="checkbox" data-s="' + k + '"' + (SND[k] ? " checked" : "") + "></label>"; };
    var pick = function(k, list){ return '<div class="xkpk">' + list.map(function(t, i){ return '<button class="xkpill' + (SND[k] === i ? " g" : " o") + '" data-p="' + k + '" data-i="' + i + '">\u25B6 ' + t[0] + "</button>"; }).join("") + "</div>"; };
    ov.innerHTML = '<div class="xklobby" style="text-align:left"><h1 style="text-align:center">\uD83D\uDD14 Sounds</h1>'
      + row("msg", "Message tone", "میسج کی آواز") + pick("msgTone", TONES)
      + row("grp", "Tone for group messages", "گروپ میسج کی آواز")
      + row("ring", "Call ringtone", "کال کی رنگ ٹون") + pick("ringTone", RINGS)
      + row("vib", "Vibrate", "وائبریٹ")
      + '<p style="font-size:.85rem;opacity:.75">When XpertCreation is closed, your phone plays its own notification sound. Muted groups stay silent.</p>'
      + '<div class="row" style="justify-content:center"><button class="xkpill g" data-close="1">Done</button></div></div>';
    B.appendChild(ov);
    ov.addEventListener("change", function(e){ var k = e.target.dataset.s; if (k){ SND[k] = e.target.checked; saveSnd(); } });
    ov.addEventListener("click", function(e){
      var b = e.target.closest("button"); if (!b) return;
      if (b.dataset.close) return ov.remove();
      if (b.dataset.p){ SND[b.dataset.p] = +b.dataset.i; saveSnd();
        [].forEach.call(ov.querySelectorAll('[data-p="' + b.dataset.p + '"]'), function(x){ x.className = "xkpill " + (x === b ? "g" : "o"); });
        var c = actx(); if (c){ if (b.dataset.p === "msgTone") TONES[+b.dataset.i][1](c, 0.09); else RINGS[+b.dataset.i][1](c); } }
    });
  }
  function ringStart(outgoing){
    ringStop(); ring.on = true;
    try { if (navigator.vibrate && !outgoing && SND.vib) navigator.vibrate([600, 400, 600, 400, 600, 400, 600]); } catch (e) {}
    if (!outgoing){
      if (!SND.ring) return;
      var rc = actx(); if (!rc) return;
      var rr = function(){ if (!ring.on) return; try { RINGS[SND.ringTone % RINGS.length][1](rc); } catch (e) {} ring.t = setTimeout(rr, 2600); };
      rr(); return;
    }
    try {
      var C = window.AudioContext || window.webkitAudioContext; if (!C) return;
      ring.ctx = ring.ctx || new C();
      var beep = function(){
        if (!ring.on) return;
        var c = ring.ctx, o = c.createOscillator(), o2 = c.createOscillator(), g = c.createGain(), t = c.currentTime;
        o.frequency.value = outgoing ? 440 : 480; o2.frequency.value = outgoing ? 480 : 620;
        g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(outgoing ? 0.05 : 0.12, t + 0.05);
        g.gain.setValueAtTime(outgoing ? 0.05 : 0.12, t + (outgoing ? 1.6 : 0.9)); g.gain.exponentialRampToValueAtTime(0.0001, t + (outgoing ? 1.8 : 1.0));
        o.connect(g); o2.connect(g); g.connect(c.destination); o.start(t); o2.start(t); o.stop(t + 2); o2.stop(t + 2);
        ring.t = setTimeout(beep, outgoing ? 4000 : 2000);
      };
      if (ring.ctx.state === "suspended") ring.ctx.resume().catch(function(){});
      beep();
    } catch (e) {}
  }
  function ringStop(){ ring.on = false; clearTimeout(ring.t); try { if (navigator.vibrate) navigator.vibrate(0); } catch (e) {} }

  /* ------------------------------------------------------------ the call */
  var CUR = null;   // the call in progress (only one at a time)
  function initials(n){ return esc((String(n || "?").trim().charAt(0) || "?").toUpperCase()); }
  function avatarStyle(a){ return a ? ' style="background-image:url(\'' + esc(a) + '\')"' : ""; }
  function fmt(s){ s = Math.max(0, Math.floor(s)); var h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = s % 60; return (h ? h + ":" + ("0" + m).slice(-2) : m) + ":" + ("0" + x).slice(-2); }

  function Call(c, opts){
    this.c = c; this.id = c.id; this.me = c.me; this.video = !!(opts && opts.video != null ? opts.video : c.video);
    this.code = c.code || ""; this.peers = {}; this.after = 0; this.stopped = false; this.muted = false; this.camOff = !this.video; this.front = true; this.screen = null;
    this.names = {}; (c.members || []).forEach(function(m){ this.names[m.id] = m; }, this);
    this.onEnd = opts && opts.onEnd;
  }
  Call.prototype.q = function(p){ return this.id + "/" + p + (this.code ? (p.indexOf("?") > -1 ? "&" : "?") + "code=" + encodeURIComponent(this.code) : ""); };
  Call.prototype.media = function(){
    var self = this;
    var want = {audio: {echoCancellation: true, noiseSuppression: true, autoGainControl: true}, video: this.video ? {facingMode: "user", width: {ideal: 1280}, height: {ideal: 720}} : false};
    return navigator.mediaDevices.getUserMedia(want).catch(function(e){
      if (self.video){ self.video = false; self.camOff = true; return navigator.mediaDevices.getUserMedia({audio: want.audio}); }
      throw e;
    }).then(function(s){ self.local = s; return s; });
  };
  Call.prototype.open = function(){
    var self = this;
    if (!navigator.mediaDevices || !window.RTCPeerConnection){ return Promise.reject(new Error("This browser can't make calls. Please update Chrome, or use the Xpert app.")); }
    this.ui();
    return api("ice/").then(function(r){ self.ice = r.iceServers || []; }).catch(function(){ self.ice = []; })
      .then(function(){ return self.media(); })
      .then(function(){ self.drawSelf(); self.loop(); })
      .catch(function(e){
        var m = e && e.name === "NotAllowedError" ? "Please allow the microphone" + (self.video ? " and camera" : "") + " for xpertcreation.com, then try again." : (e && e.message) || "Could not start the call.";
        self.say(m); setTimeout(function(){ self.hang(true); }, 3500);
        throw e;
      });
  };
  Call.prototype.ui = function(){
    var self = this, c = this.c;
    var ov = D.createElement("div"); ov.className = "xkov"; ov.setAttribute("role", "dialog"); ov.setAttribute("aria-label", "Call");
    ov.innerHTML = '<div class="xktop"><b>' + esc(c.title) + '</b><span class="xkst">' + (c.kind === "m" ? "XpertMeet" : "") + '</span>'
      + (c.kind === "m" && c.code ? '<div class="xkshare"><code>' + esc(location.origin + "/call?meet=" + c.code) + '</code><button class="xkpill" data-k="copy">' + ICON.link + ' Copy link</button></div>' : "")
      + '</div><div class="xkstage n1"></div>'
      + '<div class="xkctl">'
      + '<div class="xkcw"><button class="xkc" data-k="mute" aria-label="Mute">' + ICON.mic + '</button><div class="xklbl">Mute</div></div>'
      + '<div class="xkcw"><button class="xkc' + (this.camOff ? " off" : "") + '" data-k="cam" aria-label="Camera">' + (this.camOff ? ICON.camoff : ICON.cam) + '</button><div class="xklbl">Camera</div></div>'
      + '<div class="xkcw"><button class="xkc" data-k="flip" aria-label="Switch camera">' + ICON.flip + '</button><div class="xklbl">Flip</div></div>'
      + (navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia && !/Android|iPhone|iPad/i.test(navigator.userAgent) ? '<div class="xkcw"><button class="xkc" data-k="screen" aria-label="Share screen">' + ICON.screen + '</button><div class="xklbl">Screen</div></div>' : "")
      + '<div class="xkcw"><button class="xkc red" data-k="end" aria-label="End call">' + ICON.end + '</button><div class="xklbl">End</div></div>'
      + '</div>';
    B.appendChild(ov); this.ov = ov; this.stage = ov.querySelector(".xkstage"); this.stEl = ov.querySelector(".xkst");
    B.style.overflow = "hidden";
    ov.addEventListener("click", function(e){
      var b = e.target.closest("[data-k]"); if (!b) return;
      var k = b.dataset.k;
      if (k === "end") self.hang();
      else if (k === "mute") self.toggleMute(b);
      else if (k === "cam") self.toggleCam(b);
      else if (k === "flip") self.flip();
      else if (k === "screen") self.toggleScreen(b);
      else if (k === "copy"){ var u = location.origin + "/call?meet=" + c.code; (navigator.share ? navigator.share({title: c.title || "XpertMeet", text: "Join my XpertMeet meeting", url: u}) : navigator.clipboard.writeText(u)).then(function(){ self.say("Link ready to share."); }).catch(function(){}); }
    });
    this.status();
  };
  Call.prototype.say = function(t){
    if (!this.stage) return; var m = this.stage.querySelector(".xkmsg");
    if (!m){ m = D.createElement("div"); m.className = "xkmsg"; this.stage.appendChild(m); }
    m.textContent = t; clearTimeout(this.sayT); var mm = m; this.sayT = setTimeout(function(){ mm.remove(); }, 5000);
  };
  Call.prototype.status = function(){
    if (!this.stEl) return;
    var c = this.c, n = Object.keys(this.peers).filter(function(k){ return this.peers[k].ok; }, this).length, t = "";
    if (c.state === "ringing" && c.kind === "t") t = c.caller.id === this.me ? "Ringing…" : "Connecting…";
    else if (c.state === "ringing") t = "Waiting for others to join…";
    else if (c.answered_at && n){ t = fmt((Date.now() - this.t0) / 1000); }
    else t = "Connecting…";
    if (c.kind !== "t" && c.state !== "ringing") t += " · " + (n + 1) + " in call";
    this.stEl.textContent = (c.kind === "m" ? "XpertMeet · " : "") + t;
  };
  Call.prototype.drawSelf = function(){
    var el = this.stage.querySelector(".xkself");
    if (!el){ el = D.createElement("div"); el.className = "xkself"; el.innerHTML = '<video autoplay playsinline muted></video>'; this.stage.appendChild(el); }
    el.querySelector("video").srcObject = this.screen || this.local;
    el.classList.toggle("scr", !!this.screen);
    el.style.display = (this.camOff && !this.screen) ? "none" : "";
    this.layout();
  };
  Call.prototype.tile = function(uid){
    var t = this.stage.querySelector('.xktile[data-u="' + uid + '"]'), m = this.names[uid] || {};
    if (!t){
      t = D.createElement("div"); t.className = "xktile"; t.dataset.u = uid;
      t.innerHTML = '<div class="xkav"' + avatarStyle(m.avatar) + '>' + (m.avatar ? "" : initials(m.name)) + '</div><video autoplay playsinline style="display:none"></video><span class="xknm">' + esc(m.name || "") + '</span>';
      this.stage.insertBefore(t, this.stage.querySelector(".xkself"));
    }
    return t;
  };
  Call.prototype.layout = function(){
    var n = Math.max(1, this.stage.querySelectorAll(".xktile").length);
    this.stage.className = "xkstage n" + Math.min(4, n);
    if (!this.stage.querySelector(".xktile")){
      var w = D.createElement("div"); w.className = "xktile"; w.dataset.u = "wait";
      var c = this.c, who = c.kind === "t" ? (c.caller.id === this.me ? {name: c.title, avatar: c.avatar} : c.caller) : {name: c.title};
      w.innerHTML = '<div class="xkbig"' + avatarStyle(who.avatar) + '>' + (who.avatar ? "" : initials(who.name)) + '</div>';
      this.stage.insertBefore(w, this.stage.firstChild);
    }
  };
  Call.prototype.loop = function(){
    var self = this;
    if (this.stopped) return;
    api(this.q("poll/?after=" + this.after)).then(function(r){
      if (self.stopped) return;
      self.c = r.call; (r.call.members || []).forEach(function(m){ self.names[m.id] = m; });
      if (r.call.answered_at && !self.t0) self.t0 = Date.now() - Math.max(0, (new Date(r.call.now) - new Date(r.call.answered_at)));
      r.signals.forEach(function(s){ self.after = Math.max(self.after, s.id); self.onSignal(s); });
      if (r.call.state !== "ringing" && r.call.state !== "live"){ return self.hang(true, r.call.state); }
      var joined = r.call.members.filter(function(m){ return m.state === "joined" && m.id !== self.me; }).map(function(m){ return m.id; });
      joined.forEach(function(uid){ if (!self.peers[uid] && self.me < uid) self.connect(uid, true); });
      Object.keys(self.peers).forEach(function(uid){ if (joined.indexOf(+uid) < 0 && !self.peers[uid].fresh) self.drop(uid); });
      if (r.call.kind === "t" && r.call.state === "ringing" && r.call.caller.id === self.me){ if (!ring.on) ringStart(true); } else if (ring.on) ringStop();
      self.status();
    }).catch(function(e){ if (e.status === 404 || e.status === 410) return self.hang(true, "ended"); })
      .then(function(){
        if (self.stopped) return;
        var busy = Object.keys(self.peers).some(function(k){ return !self.peers[k].ok; });
        self.pt = setTimeout(function(){ self.loop(); }, busy || self.c.state === "ringing" ? 900 : 2000);
      });
  };
  Call.prototype.send = function(to, kind, data){ return api(this.q("signal/"), {to: +to, kind: kind, data: JSON.stringify(data), code: this.code}).catch(function(){}); };
  Call.prototype.connect = function(uid, offer){
    var self = this, pc = new RTCPeerConnection({iceServers: this.ice}), p = {pc: pc, ok: false, fresh: true, q: []};
    this.peers[uid] = p; setTimeout(function(){ p.fresh = false; }, 15000);
    (this.local ? this.local.getTracks() : []).forEach(function(t){ pc.addTrack(t, self.local); });
    if (!this.local || !this.local.getVideoTracks().length){ try { pc.addTransceiver("video", {direction: "recvonly"}); } catch (e) {} }
    if (this.screen) this.useTrack(this.screen.getVideoTracks()[0]);
    pc.onicecandidate = function(e){ if (e.candidate) self.send(uid, "ice", e.candidate); };
    pc.ontrack = function(e){
      var t = self.tile(uid), v = t.querySelector("video");
      if (v.srcObject !== e.streams[0]) v.srcObject = e.streams[0];
      var showV = function(){ var vt = e.streams[0].getVideoTracks().filter(function(x){ return x.readyState === "live" && !x.muted; }); v.style.display = vt.length ? "" : "none"; t.querySelector(".xkav").style.display = vt.length ? "none" : ""; };
      e.track.onmute = e.track.onunmute = e.track.onended = showV; showV(); self.layout();
      v.play().catch(function(){ self.say("Tap the screen to hear the call."); D.addEventListener("click", function once(){ v.play().catch(function(){}); D.removeEventListener("click", once); }); });
    };
    pc.onconnectionstatechange = function(){
      var s = pc.connectionState;
      if (s === "connected"){ p.ok = true; ringStop(); self.tile(uid); self.layout(); var w = self.stage.querySelector('[data-u="wait"]'); if (w) w.remove(); self.layout(); }
      if (s === "failed" && self.me < uid && !p.restarted){ p.restarted = true; pc.restartIce && pc.restartIce(); self.offer(uid); }
      if (s === "disconnected"){ self.say((self.names[uid] || {}).name ? self.names[uid].name + "'s connection is weak…" : "Weak connection…"); }
      self.status();
    };
    if (offer) this.offer(uid);
    return p;
  };
  Call.prototype.offer = function(uid){
    var self = this, pc = this.peers[uid].pc;
    pc.createOffer().then(function(o){ return pc.setLocalDescription(o); }).then(function(){ self.send(uid, "offer", pc.localDescription); }).catch(function(){});
  };
  Call.prototype.onSignal = function(s){
    var self = this, data; try { data = JSON.parse(s.data); } catch (e) { return; }
    var p = this.peers[s.from];
    if (s.kind === "offer"){
      if (!p) p = this.connect(s.from, false);
      p.pc.setRemoteDescription(data).then(function(){ p.q.splice(0).forEach(function(c){ p.pc.addIceCandidate(c).catch(function(){}); }); return p.pc.createAnswer(); })
        .then(function(a){ return p.pc.setLocalDescription(a); }).then(function(){ self.send(s.from, "answer", p.pc.localDescription); }).catch(function(){});
    } else if (s.kind === "answer" && p){
      p.pc.setRemoteDescription(data).then(function(){ p.q.splice(0).forEach(function(c){ p.pc.addIceCandidate(c).catch(function(){}); }); }).catch(function(){});
    } else if (s.kind === "ice" && p){
      if (p.pc.remoteDescription) p.pc.addIceCandidate(data).catch(function(){}); else p.q.push(data);
    } else if (s.kind === "bye"){ this.drop(s.from); }
  };
  Call.prototype.drop = function(uid){
    var p = this.peers[uid]; if (!p) return;
    try { p.pc.close(); } catch (e) {}
    delete this.peers[uid];
    var t = this.stage && this.stage.querySelector('.xktile[data-u="' + uid + '"]'); if (t) t.remove();
    if (this.stage) this.layout(); this.status();
  };
  Call.prototype.useTrack = function(track){
    Object.keys(this.peers).forEach(function(k){
      var pc = this.peers[k].pc, sd = pc.getSenders().filter(function(s){ return s.track && s.track.kind === "video"; })[0];
      if (sd) sd.replaceTrack(track).catch(function(){});
      else if (track){ var tr = pc.getTransceivers().filter(function(t){ return t.receiver.track && t.receiver.track.kind === "video"; })[0];
        if (tr){ tr.direction = "sendrecv"; tr.sender.replaceTrack(track).then(this.offer.bind(this, k)).catch(function(){}); } else { pc.addTrack(track, this.local); this.offer(k); } }
    }, this);
  };
  Call.prototype.toggleMute = function(b){
    this.muted = !this.muted; (this.local ? this.local.getAudioTracks() : []).forEach(function(t){ t.enabled = !this.muted; }, this);
    b.classList.toggle("off", this.muted); b.innerHTML = this.muted ? ICON.micoff : ICON.mic;
  };
  Call.prototype.toggleCam = function(b){
    var self = this, vt = this.local && this.local.getVideoTracks()[0];
    if (!vt){
      navigator.mediaDevices.getUserMedia({video: {facingMode: this.front ? "user" : "environment"}}).then(function(s){
        var t = s.getVideoTracks()[0]; self.local.addTrack(t); self.camOff = false; self.video = true;
        if (!self.screen) self.useTrack(t); b.classList.remove("off"); b.innerHTML = ICON.cam; self.drawSelf();
      }).catch(function(){ self.say("Camera is not available."); });
      return;
    }
    this.camOff = !this.camOff; vt.enabled = !this.camOff;
    b.classList.toggle("off", this.camOff); b.innerHTML = this.camOff ? ICON.camoff : ICON.cam; this.drawSelf();
  };
  Call.prototype.flip = function(){
    var self = this, old = this.local && this.local.getVideoTracks()[0];
    if (!old){ return this.say("Turn the camera on first."); }
    this.front = !this.front;
    navigator.mediaDevices.getUserMedia({video: {facingMode: this.front ? "user" : "environment"}}).then(function(s){
      var t = s.getVideoTracks()[0]; self.local.removeTrack(old); old.stop(); self.local.addTrack(t); t.enabled = !self.camOff;
      if (!self.screen) self.useTrack(t); self.drawSelf();
      var sv = self.stage.querySelector(".xkself video"); if (sv) sv.style.transform = self.front ? "" : "none";
    }).catch(function(){ self.front = !self.front; self.say("Only one camera found."); });
  };
  Call.prototype.toggleScreen = function(b){
    var self = this;
    if (this.screen){ this.screen.getTracks().forEach(function(t){ t.stop(); }); this.screen = null; var vt = this.local.getVideoTracks()[0]; this.useTrack(vt || null); b.classList.remove("off"); this.drawSelf(); return; }
    navigator.mediaDevices.getDisplayMedia({video: true, audio: false}).then(function(s){
      self.screen = s; var t = s.getVideoTracks()[0]; t.onended = function(){ if (self.screen) self.toggleScreen(b); };
      self.useTrack(t); b.classList.add("off"); self.drawSelf();
    }).catch(function(){});
  };
  Call.prototype.hang = function(remote, why){
    if (this.stopped) return; this.stopped = true; clearTimeout(this.pt); ringStop();
    var self = this;
    if (!remote){ Object.keys(this.peers).forEach(function(k){ self.send(k, "bye", {}); }); api(this.q("leave/"), {code: this.code}).catch(function(){}); }
    Object.keys(this.peers).forEach(function(k){ try { self.peers[k].pc.close(); } catch (e) {} });
    [this.local, this.screen].forEach(function(s){ if (s) s.getTracks().forEach(function(t){ t.stop(); }); });
    var msg = why === "missed" ? (this.c.caller.id === this.me ? "No answer" : "Missed call") : why === "declined" ? "Call declined" : "Call ended";
    if (this.stEl) this.stEl.textContent = msg + (this.t0 ? " · " + fmt((Date.now() - this.t0) / 1000) : "");
    var ov = this.ov; setTimeout(function(){ if (ov) ov.remove(); B.style.overflow = ""; if (self.onEnd) self.onEnd(); }, remote ? 1600 : 700);
    CUR = null;
  };

  function begin(c, opts){
    if (CUR){ return; }
    CUR = new Call(c, opts || {});
    return CUR.open().catch(function(){});
  }
  function joinAndBegin(c, video, code){
    return api(c.id + "/join/" + (code ? "?code=" + encodeURIComponent(code) : ""), {code: code || ""}).then(function(j){ return begin(j, {video: video}); });
  }
  function startCall(target, video){
    if (CUR) return;
    api("start/", Object.assign({video: !!video}, target)).then(function(c){
      if (c.members.some(function(m){ return m.id === c.me && m.state === "joined"; })) return begin(c, {video: video});
      return joinAndBegin(c, video);
    }).catch(function(e){ toast(e.status === 401 || e.status === 403 && /credentials/i.test(e.message) ? "Please sign in first." : e.message); });
  }
  function toast(t){
    var d = D.createElement("div"); d.className = "xkmsg"; d.style.position = "fixed"; d.style.top = "auto"; d.style.bottom = "90px"; d.style.zIndex = 2147483001; d.textContent = t;
    B.appendChild(d); setTimeout(function(){ d.remove(); }, 4500);
  }

  /* ------------------------------------------------------------ ringing screen */
  var ringingId = null;
  function showIncoming(c){
    if (CUR || ringingId === c.id) return; ringingId = c.id;
    var ov = D.createElement("div"); ov.className = "xkov xkring";
    ov.innerHTML = '<div class="xktop"><b>' + esc(c.caller.name) + '</b><span>' + (c.video ? "🎥 Incoming video call" : "📞 Incoming voice call") + '</span></div>'
      + '<div class="xkstage n1"><div class="xkbig"' + avatarStyle(c.caller.avatar) + '>' + (c.caller.avatar ? "" : initials(c.caller.name)) + '</div></div>'
      + '<div class="xkctl">'
      + '<div class="xkcw"><button class="xkc red" data-k="no" aria-label="Decline">' + ICON.end + '</button><div class="xklbl">Decline</div></div>'
      + (c.video ? '<div class="xkcw"><button class="xkc green" data-k="voice" aria-label="Answer with voice only">' + ICON.phone + '</button><div class="xklbl">Voice only</div></div>' : "")
      + '<div class="xkcw"><button class="xkc green" data-k="yes" aria-label="Answer">' + (c.video ? ICON.video : ICON.phone) + '</button><div class="xklbl">Answer</div></div>'
      + '</div>';
    B.appendChild(ov); ringStart(false);
    var gone = function(){ ringStop(); ov.remove(); clearInterval(chk); };
    var chk = setInterval(function(){ api(c.id + "/").then(function(x){ if (x.state !== "ringing"){ gone(); if (x.state === "missed") toast("Missed call from " + c.caller.name); } }).catch(gone); }, 2500);
    ov.addEventListener("click", function(e){
      var b = e.target.closest("[data-k]"); if (!b) return;
      gone();
      if (b.dataset.k === "no") api(c.id + "/decline/", {}).catch(function(){});
      else joinAndBegin(c, b.dataset.k === "yes" ? c.video : false).catch(function(er){ toast(er.message); });
    });
  }
  var pollT = null, lastUnread = null;
  function pollIncoming(){
    clearTimeout(pollT);
    if (D.hidden){ pollT = setTimeout(pollIncoming, 8000); return; }
    api("incoming/").then(function(r){
      if (r.call) showIncoming(r.call);
      var u = r.unread;
      if (u && lastUnread && !CUR){
        if (u.chats > lastUnread.chats) tone("chat"); else if (u.groups > lastUnread.groups) tone("grp");
      }
      if (u) lastUnread = u;
    }).catch(function(e){ if (e.status === 401 || e.status === 403) pollT = -1; })
      .then(function(){ if (pollT !== -1) pollT = setTimeout(pollIncoming, CUR ? 8000 : (PAGE === "other" ? 5000 : 3500)); });
  }

  /* ------------------------------------------------------------ buttons on chat pages */
  function btns(onVoice, onVideo){
    var w = D.createElement("span"); w.className = "xkbar";
    w.innerHTML = '<button type="button" class="xkbtn" data-v="0" aria-label="Voice call" title="Voice call">' + ICON.phone + '</button><button type="button" class="xkbtn" data-v="1" aria-label="Video call" title="Video call">' + ICON.video + '</button>';
    w.addEventListener("click", function(e){ var b = e.target.closest("button"); if (!b) return; e.stopPropagation(); (b.dataset.v === "1" ? onVideo : onVoice)(); });
    return w;
  }
  function mountIn(findTarget, make, visible){
    var bar = null;
    var place = function(){
      var t = findTarget();
      if (!t){ return; }
      if (!bar || !bar.isConnected || bar.nextSibling !== t){ if (bar) bar.remove(); bar = make(); t.parentNode.insertBefore(bar, t); }
      bar.style.display = visible && !visible() ? "none" : "";
    };
    new MutationObserver(place).observe(B, {childList: true, subtree: true}); setInterval(place, 1500); place();
  }
  function chatButtons(){
    mountIn(function(){ return D.querySelector(".thd3 .more3"); },
      function(){ return btns(function(){ var c = XC3.cur(); if (c) startCall({thread: c.id}, false); }, function(){ var c = XC3.cur(); if (c) startCall({thread: c.id}, true); }); },
      function(){ return !!(window.XC3 && XC3.cur && XC3.cur()); });
    openTone("msgs3");
  }
  function openTone(id){
    var lastAct = 0, seen = null;
    ["keydown", "pointerdown"].forEach(function(ev){ D.addEventListener(ev, function(){ lastAct = Date.now(); }, true); });
    setInterval(function(){
      var box = $(id); if (!box) return;
      if (seen !== box){ seen = box; box._xkn = box.children.length;
        new MutationObserver(function(){ var n = box.children.length; if (n > box._xkn && Date.now() - lastAct > 2500 && !D.hidden && !CUR) tone("open"); box._xkn = n; }).observe(box, {childList: true}); }
    }, 1500);
  }
  function groupButtons(){
    var gid = function(){ return (window.XCG && XCG.gid && XCG.gid()) || (location.pathname.match(/\/group\/(\d+)/) || [])[1]; };
    mountIn(function(){ return D.querySelector('.gh [aria-label="Group info"]') || D.querySelector(".gh .gbtn:last-child"); },
      function(){ return btns(function(){ startCall({group: +gid()}, false); }, function(){ startCall({group: +gid()}, true); }); });
    openTone("glog");
    var banner = null;
    var check = function(){
      if (CUR || D.hidden || !gid()) return;
      api("active/?group=" + gid()).then(function(r){
        var c = r.call, joinedMe = c && c.members.some(function(m){ return m.id === c.me && m.state === "joined"; });
        if (c && !joinedMe){
          var n = c.members.filter(function(m){ return m.state === "joined"; }).length;
          if (!banner){ banner = D.createElement("button"); banner.className = "xkjoin"; banner.type = "button"; var host = D.querySelector(".wrap") || B; host.insertBefore(banner, host.firstChild);
            banner.addEventListener("click", function(){ var cc = banner._c; if (cc) joinAndBegin(cc, cc.video).catch(function(e){ toast(e.message); }); }); }
          banner._c = c; banner.innerHTML = (c.video ? ICON.video : ICON.phone) + "<span>" + esc(c.caller.name) + " started a " + (c.video ? "video" : "voice") + " call · " + n + "/" + c.max + " · Tap to join</span>";
        } else if (banner){ banner.remove(); banner = null; }
      }).catch(function(){});
    };
    check(); setInterval(check, 8000);
  }
  function menuLink(){
    new MutationObserver(function(){
      var m = D.querySelector(".xcmenu"); if (!m || m.querySelector("[data-xkmeet]")) return;
      var a = D.createElement("a"); a.href = "/call?new=1"; a.setAttribute("data-xkmeet", "1"); a.textContent = "\uD83C\uDFA5 XpertMeet (video meeting)";
      var cls = m.querySelector("a"); if (cls) a.className = cls.className;
      var a2 = D.createElement("a"); a2.href = "#xksounds"; a2.textContent = "\uD83D\uDD14 Sounds"; if (cls) a2.className = cls.className;
      a2.addEventListener("click", function(e){ e.preventDefault(); m.remove(); soundsPanel(); });
      m.appendChild(a); m.appendChild(a2);
    }).observe(B, {childList: true});
  }

  /* ------------------------------------------------------------ meeting times around the world */
  var ZONES = [["\uD83C\uDDF5\uD83C\uDDF0", "Pakistan", "Asia/Karachi"], ["\uD83C\uDDEE\uD83C\uDDF3", "India", "Asia/Kolkata"], ["\uD83C\uDDE7\uD83C\uDDE9", "Bangladesh", "Asia/Dhaka"],
    ["\uD83C\uDDE6\uD83C\uDDEA", "UAE", "Asia/Dubai"], ["\uD83C\uDDF8\uD83C\uDDE6", "Saudi Arabia", "Asia/Riyadh"], ["\uD83C\uDDF9\uD83C\uDDF7", "Turkey", "Europe/Istanbul"],
    ["\uD83C\uDDEC\uD83C\uDDE7", "UK", "Europe/London"], ["\uD83C\uDDE9\uD83C\uDDEA", "Germany", "Europe/Berlin"], ["\uD83C\uDDFA\uD83C\uDDF8", "USA New York", "America/New_York"],
    ["\uD83C\uDDFA\uD83C\uDDF8", "USA Chicago", "America/Chicago"], ["\uD83C\uDDFA\uD83C\uDDF8", "USA Los Angeles", "America/Los_Angeles"], ["\uD83C\uDDE8\uD83C\uDDE6", "Canada Toronto", "America/Toronto"],
    ["\uD83C\uDDE8\uD83C\uDDF3", "China", "Asia/Shanghai"], ["\uD83C\uDDEF\uD83C\uDDF5", "Japan", "Asia/Tokyo"], ["\uD83C\uDDE6\uD83C\uDDFA", "Australia Sydney", "Australia/Sydney"]];
  function dayKey(d, tz){ return new Intl.DateTimeFormat("en-CA", {timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit"}).format(d); }
  function timeIn(d, tz, base){
    var t = new Intl.DateTimeFormat("en-US", {timeZone: tz, hour: "numeric", minute: "2-digit"}).format(d);
    var a = dayKey(d, tz), b = dayKey(d, base);
    return t + (a > b ? " (next day)" : a < b ? " (day before)" : "");
  }
  function dateIn(d, tz){ return new Intl.DateTimeFormat("en-GB", {timeZone: tz, weekday: "long", day: "numeric", month: "long", year: "numeric"}).format(d); }
  function myZone(){ try { return Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Karachi"; } catch (e) { return "Asia/Karachi"; } }
  function meetUrl(c){ return location.origin + "/call?meet=" + c.code; }
  function inviteText(c){
    var d = new Date(c.starts_at), base = "Asia/Karachi";
    var lines = ["\uD83C\uDFA5 You're invited to an XpertMeet meeting" + (c.title ? ": " + c.title : ""), "Host: " + c.caller.name, "",
      "\uD83D\uDCC5 " + dateIn(d, base) + " (Pakistan date)", "\u23F0 Time around the world:"];
    ZONES.forEach(function(z){ lines.push(z[0] + " " + z[1] + ": " + timeIn(d, z[2], base)); });
    lines.push("", "\uD83D\uDC49 Join here: " + meetUrl(c), "Free on XpertCreation \u00B7 up to " + c.max + " people \u00B7 sign in to join");
    return lines.join("\n");
  }
  function icsFile(c){
    var d = new Date(c.starts_at), e = new Date(d.getTime() + 60 * 60000);
    var f = function(x){ return x.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, ""); };
    var t = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//XpertCreation//XpertMeet//EN", "BEGIN:VEVENT", "UID:" + c.code + "@xpertcreation.com", "DTSTAMP:" + f(new Date()),
      "DTSTART:" + f(d), "DTEND:" + f(e), "SUMMARY:" + (c.title || "XpertMeet meeting").replace(/[\n,;]/g, " "), "DESCRIPTION:Join: " + meetUrl(c), "URL:" + meetUrl(c), "END:VEVENT", "END:VCALENDAR"].join("\r\n");
    var a = D.createElement("a"); a.href = URL.createObjectURL(new Blob([t], {type: "text/calendar"})); a.download = "XpertMeet-" + c.code + ".ics"; B.appendChild(a); a.click(); setTimeout(function(){ a.remove(); }, 500);
  }
  function inviteBox(c){
    var d = new Date(c.starts_at), z = myZone();
    return '<div class="xkinv"><p><b>' + esc(dateIn(d, z)) + ', ' + esc(timeIn(d, z, z)) + '</b> <span style="opacity:.75">(your time)</span></p>'
      + '<div class="xktz">' + ZONES.map(function(q){ return '<span>' + q[0] + " " + esc(q[1]) + " <b>" + esc(timeIn(d, q[2], "Asia/Karachi")) + "</b></span>"; }).join("") + '</div>'
      + '<div class="row"><button class="xkpill g" data-i="copy">\uD83D\uDCCB Copy invitation</button><a class="xkpill" style="background:#25D366;color:#fff" target="_blank" rel="noopener" href="https://wa.me/?text=' + encodeURIComponent(inviteText(c)) + '">WhatsApp</a><button class="xkpill o" data-i="ics">\uD83D\uDCC5 Add to calendar</button></div></div>';
  }
  function wireInvite(root, c){
    root.addEventListener("click", function(e){
      var b = e.target.closest("[data-i]"); if (!b) return;
      if (b.dataset.i === "ics") return icsFile(c);
      var t = inviteText(c);
      (navigator.clipboard ? navigator.clipboard.writeText(t) : Promise.reject()).then(function(){ b.textContent = "\u2714 Copied"; }).catch(function(){ window.prompt("Copy the invitation:", t); });
    });
  }

  /* ------------------------------------------------------------ the /call page */
  function lobby(html){
    var ov = D.querySelector(".xkov.xkl");
    if (!ov){ ov = D.createElement("div"); ov.className = "xkov xkl"; B.appendChild(ov); }
    ov.innerHTML = '<div class="xklobby"><img src="/brand/xpertchat/mark-128.webp" width="64" height="64" alt="">' + html + '</div>';
    return ov;
  }
  function home(){ location.href = "/chat"; }
  function callPage(){
    var q = new URLSearchParams(location.search), id = q.get("id"), meet = (q.get("meet") || "").toLowerCase().replace(/[^a-z-]/g, "");
    var signin = function(){ lobby('<h1>Sign in to join</h1><p>Calls and meetings are for XpertCreation members.<span class="xkur" dir="rtl" lang="ur">کال اور میٹنگ کے لیے سائن ان کریں۔</span></p><div class="row"><a class="xkpill g" href="/login?next=' + encodeURIComponent(location.pathname + location.search) + '">Sign in</a><a class="xkpill o" href="/register">Join free</a></div>'); };
    var fail = function(e){ if (e.status === 401 || e.status === 403 && !/full|admins/i.test(e.message)) return signin(); lobby('<h1>Can\'t open this</h1><p class="er">' + esc(e.message) + '</p><div class="row"><a class="xkpill o" href="/chat">Back to XpertChat</a></div>'); };
    if (id && /^\d+$/.test(id)){
      api(id + "/").then(function(c){
        if (c.state !== "ringing" && c.state !== "live"){ return lobby("<h1>" + esc(c.title) + "</h1><p>This call has ended.</p><div class=\"row\"><a class=\"xkpill o\" href=\"" + esc(c.link) + "\">Open the chat</a></div>"); }
        var me = c.members.filter(function(m){ return m.id === c.me; })[0];
        if (c.kind === "t" && me && me.state === "ringing"){
          var l = lobby("<h1>" + esc(c.caller.name) + "</h1><p>" + (c.video ? "🎥 Video call" : "📞 Voice call") + "</p><div class=\"row\"><button class=\"xkpill\" style=\"background:#e53935;color:#fff\" data-k=\"no\">Decline</button>" + (c.video ? "<button class=\"xkpill g\" data-k=\"voice\">Voice only</button>" : "") + "<button class=\"xkpill g\" data-k=\"yes\">Answer</button></div>");
          l.addEventListener("click", function(e){ var b = e.target.closest("[data-k]"); if (!b) return;
            if (b.dataset.k === "no") return api(c.id + "/decline/", {}).then(home, home);
            l.remove(); joinAndBegin(c, b.dataset.k === "yes" ? c.video : false).then(function(){ if (CUR) CUR.onEnd = function(){ location.href = c.link; }; }).catch(fail); });
          return;
        }
        var l2 = lobby("<h1>" + esc(c.title) + "</h1><p>" + (c.video ? "Video" : "Voice") + " call · " + c.members.filter(function(m){ return m.state === "joined"; }).length + " in the call</p><div class=\"row\"><button class=\"xkpill g\" data-k=\"go\">Join now</button><a class=\"xkpill o\" href=\"" + esc(c.link) + "\">Back</a></div>");
        l2.querySelector("[data-k=go]").addEventListener("click", function(){ l2.remove(); joinAndBegin(c, c.video).then(function(){ if (CUR) CUR.onEnd = function(){ location.href = c.link; }; }).catch(fail); });
      }).catch(fail);
      return;
    }
    if (meet){
      api("meet/" + meet + "/").then(function(c){
        if (c.state !== "ringing" && c.state !== "live") return lobby("<h1>" + esc(c.title) + "</h1><p>This meeting has ended. Ask the host for a new link.</p><div class=\"row\"><a class=\"xkpill g\" href=\"/call?new=1\">Start your own meeting</a></div>");
        var joinedN = c.members.filter(function(m){ return m.state === "joined"; }).length;
        var later = c.starts_at && new Date(c.starts_at) > new Date(Date.now() + 60000);
        var l = lobby("<h1>" + esc(c.title || "XpertMeet meeting") + "</h1><p>Hosted by " + esc(c.caller.name) + " \u00B7 " + joinedN + "/" + c.max + " in the meeting</p>"
          + (c.starts_at ? inviteBox(c) : "")
          + "<div class=\"row\"><button class=\"xkpill g\" data-v=\"1\">\uD83C\uDFA5 " + (later ? "Join early with video" : "Join with video") + "</button><button class=\"xkpill o\" data-v=\"0\">\uD83C\uDFA4 Voice only</button></div><p class=\"er\"></p>");
        if (c.starts_at) wireInvite(l, c);
        l.addEventListener("click", function(e){ var b = e.target.closest("[data-v]"); if (!b) return;
          joinAndBegin(c, b.dataset.v === "1", meet).then(function(){ l.remove(); if (CUR) CUR.onEnd = function(){ lobby("<h1>You left the meeting</h1><div class=\"row\"><a class=\"xkpill g\" href=\"" + location.pathname + location.search + "\">Rejoin</a><a class=\"xkpill o\" href=\"/chat\">XpertChat</a></div>"); }; })
            .catch(function(er){ l.querySelector(".er").textContent = er.message; if (er.status === 401) signin(); }); });
      }).catch(fail);
      return;
    }
    var l = lobby('<h1>XpertMeet</h1><p>Video meetings on XpertCreation · up to 4 people · free<span class="xkur" dir="rtl" lang="ur">ایکسپرٹ میٹ: مفت ویڈیو میٹنگ، 4 افراد تک</span></p>'
      + '<input maxlength="80" placeholder="Meeting name (optional)" aria-label="Meeting name"><div class="row"><button class="xkpill g" data-v="1">\uD83C\uDFA5 Start video meeting now</button><button class="xkpill o" data-v="0">\uD83C\uDFA4 Voice meeting</button></div>'
      + '<label>Or schedule it for later (your time, ' + esc(myZone()) + '):</label><input type="datetime-local" aria-label="Meeting date and time"><div class="row"><button class="xkpill g" data-s="1">\uD83D\uDCC5 Schedule and get the invitation</button></div><div class="xkmine"></div>'
      + '<p style="margin-top:18px">Have a link? Paste it here:</p><input placeholder="xpertcreation.com/call?meet=abc-defg-hij" aria-label="Meeting link"><div class="row"><button class="xkpill o" data-j="1">Join</button></div><p class="er"></p>');
    api("meet/mine/").then(function(r){ var box = l.querySelector(".xkmine"); if (!box || !r.meetings.length) return;
      box.innerHTML = '<p style="margin-top:16px"><b>Your meetings coming up</b></p>' + r.meetings.map(function(c){ return '<p><a style="color:#8ab4ff" href="/call?meet=' + esc(c.code) + '">' + esc(c.title || "Meeting") + " \u00B7 " + esc(dateIn(new Date(c.starts_at), myZone())) + ", " + esc(timeIn(new Date(c.starts_at), myZone(), myZone())) + "</a></p>"; }).join(""); }).catch(function(){});
    l.addEventListener("click", function(e){
      var b = e.target.closest("button"); if (!b) return; var ins = l.querySelectorAll("input"), er = l.querySelector(".er");
      if (b.dataset.j){ var m = (ins[2].value.match(/meet=([a-z-]+)/i) || [null, ins[2].value.trim()])[1]; if (m) location.href = "/call?meet=" + encodeURIComponent(m.toLowerCase()); return; }
      if (b.dataset.s){
        if (!ins[1].value){ er.textContent = "Pick the date and time first."; return; }
        var when = new Date(ins[1].value); if (isNaN(when)){ er.textContent = "That date is not valid."; return; }
        b.disabled = true;
        return api("meet/new/", {title: ins[0].value.trim(), video: true, when: when.toISOString()}).then(function(c){
          history.replaceState(null, "", "/call?meet=" + c.code);
          var l3 = lobby("<h1>Meeting scheduled \u2714</h1><p>" + esc(c.title || "XpertMeet meeting") + "</p>" + inviteBox(c) + '<div class="xkshare"><code>' + esc(meetUrl(c)) + '</code></div><div class="row"><a class="xkpill o" href="/call?meet=' + esc(c.code) + '">Open the meeting page</a></div>');
          wireInvite(l3, c);
        }).catch(function(e3){ b.disabled = false; if (e3.status === 401 || e3.status === 403) return signin(); er.textContent = e3.message; });
      }
      b.disabled = true;
      api("meet/new/", {title: ins[0].value.trim(), video: b.dataset.v === "1"}).then(function(c){
        history.replaceState(null, "", "/call?meet=" + c.code);
        l.remove(); begin(c, {video: b.dataset.v === "1"}); if (CUR) CUR.onEnd = function(){ lobby("<h1>Meeting ended</h1><div class=\"row\"><a class=\"xkpill g\" href=\"/call?new=1\">New meeting</a><a class=\"xkpill o\" href=\"/chat\">XpertChat</a></div>"); };
      }).catch(function(e2){ b.disabled = false; if (e2.status === 401 || e2.status === 403) return signin(); er.textContent = e2.message; });
    });
  }

  window.XCCALL = { start: startCall, begin: begin, sounds: soundsPanel, tone: tone, _ring: showIncoming };
  if (PAGE === "call") callPage();
  else {
    if (PAGE === "chat") chatButtons();
    if (PAGE === "group") groupButtons();
    menuLink();
    pollIncoming();
    D.addEventListener("visibilitychange", function(){ if (!D.hidden && pollT !== -1) pollIncoming(); });
  }
})();
