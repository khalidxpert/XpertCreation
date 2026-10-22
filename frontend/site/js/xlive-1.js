/* Go Live on XpertConnect (xpertcreation.com/live). Video through our own LiveKit server.
   /live            - who is live now + the Go Live button
   /live?go=1       - camera check, title, Start live
   /live?id=N       - watch (comments, hearts, share); the host sees the same page with controls:
                      viewers list, invite a viewer on screen, remove someone, flip camera, mute, end. */
(function(){
  "use strict";
  var D = document, B = D.body, LK = window.LivekitClient, Q = new URLSearchParams(location.search);
  var app = D.getElementById("xlive") || (function(){ var d = D.createElement("div"); d.id = "xlive"; B.appendChild(d); return d; })();
  var enc = new TextEncoder(), dec = new TextDecoder();

  function esc(s){ return String(s == null ? "" : s).replace(/[&<>"']/g, function(c){ return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]; }); }
  function ck(n){ var m = D.cookie.match(new RegExp("(?:^|; )" + n + "=([^;]*)")); return m ? decodeURIComponent(m[1]) : ""; }
  function api(url, body){
    var o = {method: body ? "POST" : "GET", credentials: "same-origin", headers: {"X-CSRFToken": ck("xc_csrf")}};
    if (body){ o.body = JSON.stringify(body); o.headers["Content-Type"] = "application/json"; }
    return fetch("/api/live/" + url, o).then(function(r){ return r.json().catch(function(){ return {}; }).then(function(d){ d._s = r.status; d._ok = r.ok; return d; }); });
  }
  function toast(t){ var e = D.createElement("div"); e.className = "lv-toast"; e.textContent = t; B.appendChild(e); setTimeout(function(){ e.remove(); }, 2600); }
  function av(h){ return h.avatar ? '<img src="' + esc(h.avatar) + '" alt="">' : "<b>" + esc((h.name || "?").charAt(0).toUpperCase()) + "</b>"; }
  function clock(s){ s = Math.max(0, s | 0); var h = s / 3600 | 0, m = (s % 3600) / 60 | 0, x = s % 60; return (h ? h + ":" + ("0" + m).slice(-2) : m) + ":" + ("0" + x).slice(-2); }

  var css = D.createElement("style");
  css.textContent = [
    "html,body{margin:0;background:#07090F;color:#fff;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;height:100%}",
    ".lv-wrap{max-width:720px;margin:0 auto;padding:14px 14px 40px}",
    ".lv-top{display:flex;align-items:center;gap:10px;padding:4px 0 14px}.lv-top a{color:#fff;text-decoration:none;font-size:22px}.lv-top h1{flex:1;margin:0;font-size:22px;font-weight:900}",
    ".lv-go{border:0;border-radius:99px;background:#E11D48;color:#fff;font:inherit;font-weight:900;font-size:15px;padding:11px 18px;cursor:pointer;box-shadow:0 6px 18px rgba(225,29,72,.4)}",
    ".lv-go:disabled{opacity:.55}",
    ".lv-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px}",
    ".lv-card{position:relative;aspect-ratio:3/4;border-radius:18px;overflow:hidden;background:linear-gradient(160deg,#1B2340,#0B1530);text-decoration:none;color:#fff;display:flex;flex-direction:column;justify-content:flex-end;padding:12px}",
    ".lv-card .av{position:absolute;left:50%;top:38%;transform:translate(-50%,-50%);width:86px;height:86px;border-radius:50%;border:3px solid #E11D48;overflow:hidden;display:grid;place-items:center;background:#1B4DFF;font-size:34px}",
    ".lv-card .av img{width:100%;height:100%;object-fit:cover}",
    ".lv-badge{display:inline-flex;align-items:center;gap:5px;background:#E11D48;color:#fff;border-radius:7px;padding:3px 8px;font-size:12px;font-weight:900;letter-spacing:.04em}",
    ".lv-badge i{width:7px;height:7px;border-radius:50%;background:#fff;animation:lvb 1.2s infinite}@keyframes lvb{50%{opacity:.25}}",
    ".lv-card .lv-badge{position:absolute;left:10px;top:10px}.lv-card .eye{position:absolute;right:10px;top:10px;background:rgba(0,0,0,.45);border-radius:7px;padding:3px 7px;font-size:12px;font-weight:800}",
    ".lv-card b.t{font-size:14px;line-height:1.25}.lv-card small{opacity:.75;font-size:12px}",
    ".lv-empty{text-align:center;padding:50px 10px;opacity:.85}.lv-empty div{font-size:54px}",
    ".lv-stage{position:fixed;inset:0;background:#000;overflow:hidden}",
    ".lv-stage video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;background:#000}",
    ".lv-stage video.fit{object-fit:contain}",
    ".lv-pip{position:absolute;right:12px;top:72px;width:30%;max-width:170px;aspect-ratio:3/4;border-radius:14px;overflow:hidden;border:2px solid #fff;background:#111;z-index:3}",
    ".lv-pip video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}",
    ".lv-hud{position:absolute;left:0;right:0;top:0;padding:calc(10px + env(safe-area-inset-top)) 12px 30px;display:flex;align-items:center;gap:8px;background:linear-gradient(rgba(0,0,0,.55),transparent);z-index:4}",
    ".lv-hud .who{display:flex;align-items:center;gap:8px;flex:1;min-width:0}.lv-hud .who .a{width:36px;height:36px;border-radius:50%;overflow:hidden;background:#1B4DFF;display:grid;place-items:center;flex:0 0 auto}.lv-hud .who .a img{width:100%;height:100%;object-fit:cover}",
    ".lv-hud .who span{display:flex;flex-direction:column;min-width:0}.lv-hud .who b{font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.lv-hud .who small{font-size:12px;opacity:.85}",
    ".lv-pill{background:rgba(0,0,0,.45);border-radius:8px;padding:4px 8px;font-size:12.5px;font-weight:800;border:0;color:#fff;font-family:inherit;cursor:pointer}",
    ".lv-x{width:36px;height:36px;border-radius:50%;border:0;background:rgba(0,0,0,.45);color:#fff;font-size:18px;cursor:pointer}",
    ".lv-feed{position:absolute;left:12px;right:86px;bottom:calc(76px + env(safe-area-inset-bottom));z-index:4;display:flex;flex-direction:column;gap:6px;max-height:40vh;overflow:hidden;-webkit-mask-image:linear-gradient(transparent,#000 30%)}",
    ".lv-c{align-self:flex-start;background:rgba(0,0,0,.42);border-radius:14px;padding:6px 10px;font-size:14px;line-height:1.35;max-width:100%;word-wrap:break-word;animation:lvin .25s}",
    ".lv-c b{color:#FFD166;margin-right:6px}.lv-c.sys{background:rgba(27,77,255,.55)}@keyframes lvin{from{opacity:0;transform:translateY(8px)}}",
    ".lv-bar{position:absolute;left:0;right:0;bottom:0;z-index:5;display:flex;gap:8px;align-items:center;padding:10px 12px calc(12px + env(safe-area-inset-bottom));background:linear-gradient(transparent,rgba(0,0,0,.6))}",
    ".lv-bar input{flex:1;min-width:0;border:0;border-radius:99px;padding:12px 16px;font:inherit;font-size:15px;background:rgba(255,255,255,.16);color:#fff;outline:none}.lv-bar input::placeholder{color:rgba(255,255,255,.75)}",
    ".lv-b{width:46px;height:46px;flex:0 0 46px;border-radius:50%;border:0;background:rgba(255,255,255,.16);color:#fff;font-size:21px;cursor:pointer;display:grid;place-items:center}",
    ".lv-b.red{background:#E11D48}.lv-b.off{background:#fff;color:#111}",
    ".lv-heart{position:absolute;right:22px;bottom:90px;z-index:6;font-size:30px;pointer-events:none;animation:lvh 2.2s ease-out forwards}",
    "@keyframes lvh{0%{opacity:1;transform:translate(0,0) scale(.6)}100%{opacity:0;transform:translate(var(--dx),-46vh) scale(1.3)}}",
    ".lv-mid{position:absolute;inset:0;display:grid;place-items:center;text-align:center;z-index:2;padding:20px}",
    ".lv-mid h2{margin:10px 0 6px;font-size:22px}.lv-mid p{opacity:.85;margin:0 0 14px}",
    ".lv-sh{position:fixed;inset:0;z-index:20;background:rgba(0,0,0,.55);display:flex;align-items:flex-end;justify-content:center}",
    ".lv-box{background:#12172A;color:#fff;width:100%;max-width:520px;max-height:80vh;overflow:auto;border-radius:22px 22px 0 0;padding:16px 16px calc(16px + env(safe-area-inset-bottom))}",
    ".lv-box h3{margin:0 0 10px}.lv-row{display:flex;align-items:center;gap:8px;padding:9px 0;border-bottom:1px solid rgba(255,255,255,.08)}.lv-row span{flex:1}",
    ".lv-row button,.lv-box .btn{border:0;border-radius:10px;padding:8px 11px;font:inherit;font-size:13px;font-weight:800;cursor:pointer;background:#1B4DFF;color:#fff}",
    ".lv-row button.g{background:#2A3150}.lv-row button.r{background:#7F1D1D}",
    ".lv-prep input{width:100%;box-sizing:border-box;border:0;border-radius:14px;padding:14px;font:inherit;font-size:16px;background:rgba(255,255,255,.14);color:#fff;outline:none}",
    ".lv-prep{position:absolute;left:0;right:0;bottom:0;z-index:5;padding:16px 16px calc(18px + env(safe-area-inset-bottom));background:linear-gradient(transparent,rgba(0,0,0,.8) 30%);display:flex;flex-direction:column;gap:10px}",
    ".lv-prep .row{display:flex;gap:8px;justify-content:center}",
    ".lv-toast{position:fixed;left:50%;top:84px;transform:translateX(-50%);background:rgba(13,20,36,.92);color:#fff;padding:10px 16px;border-radius:12px;font-size:14px;z-index:30}",
    ".lv-share{display:flex;gap:8px;flex-wrap:wrap}"
  ].join("\n");
  D.head.appendChild(css);

  if (!LK){ app.innerHTML = '<div class="lv-wrap"><p>Live could not load. Please reload the page.</p></div>'; return; }

  /* ------------------------------------------------------------------ list */
  function list(){
    app.innerHTML = '<div class="lv-wrap"><div class="lv-top"><a href="/feed" aria-label="Back">←</a><h1>🔴 Live</h1><button class="lv-go" data-go>🔴 Go Live</button></div><div data-list><p style="opacity:.7">Loading…</p></div>'
      + '<p style="opacity:.65;font-size:13px;margin-top:22px">Go live from your phone: your followers and connections get a notification. Viewers can comment and send hearts, and you can invite someone to join you on screen.</p></div>';
    var draw = function(){
      api("").then(function(d){
        var box = app.querySelector("[data-list]"); if (!box) return;
        var L = d.lives || [];
        box.innerHTML = L.length ? '<div class="lv-grid">' + L.map(function(l){
          return '<a class="lv-card" href="' + l.url + '"><span class="lv-badge"><i></i>LIVE</span><span class="eye">👁 ' + l.viewers + '</span><span class="av">' + av(l.host) + '</span><b class="t">' + esc(l.title) + "</b><small>" + esc(l.host.name) + " · " + clock(l.seconds) + "</small></a>";
        }).join("") + "</div>" : '<div class="lv-empty"><div>🎥</div><p>No one is live right now.<br>Be the first — tap <b>Go Live</b>.</p></div>';
        if (d.mine) box.insertAdjacentHTML("afterbegin", '<p><a class="lv-go" style="text-decoration:none;display:inline-block" href="/live?id=' + d.mine + '">Back to your live</a></p>');
      });
    };
    draw(); var t = setInterval(function(){ if (!D.contains(app.querySelector("[data-list]"))) return clearInterval(t); draw(); }, 20000);
    app.querySelector("[data-go]").onclick = function(){ location.href = "/live?go=1"; };
  }

  /* ------------------------------------------------------------------ camera check before going live */
  function prep(){
    var tracks = [], facing = "user", micOn = true;
    app.innerHTML = '<div class="lv-stage"><video playsinline muted autoplay></video><div class="lv-hud"><button class="lv-x" data-x>✕</button><span style="flex:1"></span><span class="lv-pill">Camera check</span></div>'
      + '<div class="lv-prep"><input data-title maxlength="120" placeholder="What is your live about? (title)"><div class="row"><button class="lv-b" data-flip title="Flip camera">🔄</button><button class="lv-b" data-mic title="Microphone">🎙️</button></div>'
      + '<button class="lv-go" data-start style="padding:15px">🔴 Start live</button><small style="opacity:.75;text-align:center">Followers and connections get a notification. Be kind — lives follow the XpertCreation rules.</small></div></div>';
    var vid = app.querySelector("video");
    function cam(){
      tracks.forEach(function(t){ t.stop(); });
      return LK.createLocalTracks({audio: true, video: {facingMode: facing, resolution: LK.VideoPresets.h720.resolution}}).then(function(t){
        tracks = t; var v = t.filter(function(x){ return x.kind === "video"; })[0]; if (v) v.attach(vid);
        var a = t.filter(function(x){ return x.kind === "audio"; })[0]; if (a && !micOn) a.mute();
        vid.style.transform = facing === "user" ? "scaleX(-1)" : "";
      }).catch(function(e){ app.querySelector(".lv-prep").innerHTML = '<p style="text-align:center">Please allow the camera and microphone for this site, then reload. (' + esc(e.message || e.name || "") + ")</p>"; });
    }
    cam();
    app.querySelector("[data-x]").onclick = function(){ tracks.forEach(function(t){ t.stop(); }); location.href = "/live"; };
    app.querySelector("[data-flip]").onclick = function(){ facing = facing === "user" ? "environment" : "user"; cam(); };
    app.querySelector("[data-mic]").onclick = function(){ micOn = !micOn; this.classList.toggle("off", !micOn); this.textContent = micOn ? "🎙️" : "🔇"; tracks.forEach(function(t){ if (t.kind === "audio"){ if (micOn) t.unmute(); else t.mute(); } }); };
    app.querySelector("[data-start]").onclick = function(){
      var b = this; b.disabled = true; b.textContent = "Starting…";
      api("start/", {title: app.querySelector("[data-title]").value}).then(function(d){
        if (d._s === 401 || d._s === 403){ location.href = "/login?next=" + encodeURIComponent("/live?go=1"); return; }
        if (!d._ok){ toast(d.detail || "Could not start."); b.disabled = false; b.textContent = "🔴 Start live"; return; }
        history.replaceState(null, "", "/live?id=" + d.live.id);
        room(d, tracks, facing, micOn);
      }).catch(function(){ toast("No internet. Try again."); b.disabled = false; b.textContent = "🔴 Start live"; });
    };
  }

  /* ------------------------------------------------------------------ the live room (host and viewers) */
  function room(d, preTracks, facing, micOn){
    var L = d.live, host = !!L.mine, me = d.me || {}, R = new LK.Room({adaptiveStream: true, dynacast: true}), hearts = L.hearts || 0, started = Date.parse(L.started), lock = null, ended = false;
    facing = facing || "user";
    app.innerHTML = '<div class="lv-stage"><video playsinline autoplay data-main></video><div class="lv-pip" data-pip style="display:none"><video playsinline autoplay></video></div>'
      + '<div class="lv-mid" data-mid><div><div style="font-size:40px">⏳</div><p>Connecting…</p></div></div>'
      + '<div class="lv-hud"><div class="who"><span class="a">' + av(L.host) + '</span><span><b>' + esc(L.host.name) + '</b><small>' + esc(L.title) + '</small></span></div>'
      + '<span class="lv-badge"><i></i>LIVE <em data-time style="font-style:normal">0:00</em></span><button class="lv-pill" data-eye>👁 <span data-n>0</span></button><button class="lv-x" data-x>✕</button></div>'
      + '<div class="lv-feed" data-feed></div><div class="lv-bar">'
      + (me.guest ? '<a class="lv-pill" href="/login?next=' + encodeURIComponent("/live?id=" + L.id) + '" style="flex:1;text-align:center;padding:12px;text-decoration:none">Sign in to comment</a>' : '<input data-say maxlength="200" placeholder="Say something…"><button class="lv-b" data-send>➤</button>')
      + (host ? '<button class="lv-b" data-flip>🔄</button><button class="lv-b" data-mic>🎙️</button><button class="lv-b red" data-end title="End live">⏹</button>' : '<button class="lv-b" data-share>↗️</button><button class="lv-b" data-heart style="color:#FF4D6D">❤</button>')
      + "</div></div>";
    var $ = function(s){ return app.querySelector(s); }, mainV = $("[data-main]"), pip = $("[data-pip]"), pipV = pip.querySelector("video"), feed = $("[data-feed]");
    mainV.muted = true; pipV.muted = true;      // sound plays through separate audio players (below)
    var soundBtn = null;
    function soundCheck(){
      if (host) return;
      if (R.canPlaybackAudio){ if (soundBtn){ soundBtn.remove(); soundBtn = null; } return; }
      if (soundBtn) return;
      soundBtn = D.createElement("button"); soundBtn.className = "lv-go"; soundBtn.textContent = "\uD83D\uDD0A Tap for sound";
      soundBtn.style.cssText = "position:absolute;left:50%;top:42%;transform:translateX(-50%);z-index:7";
      soundBtn.onclick = function(){ R.startAudio().then(soundCheck).catch(function(){}); };
      $(".lv-stage").appendChild(soundBtn);
    }
    app.addEventListener("click", function(){ if (!R.canPlaybackAudio) R.startAudio().then(soundCheck).catch(function(){}); }, true);
    var timer = setInterval(function(){ $("[data-time]").textContent = clock((Date.now() - started) / 1000); if (R.state === "connected") $("[data-n]").textContent = R.remoteParticipants.size; }, 1000);
    function say(name, text, sys){ var e = D.createElement("div"); e.className = "lv-c" + (sys ? " sys" : ""); e.innerHTML = (name ? "<b>" + esc(name) + "</b>" : "") + esc(text); feed.appendChild(e); while (feed.children.length > 30) feed.firstChild.remove(); }
    function heart(){ var h = D.createElement("div"); h.className = "lv-heart"; h.textContent = ["❤️", "💖", "💗", "🧡", "💜"][Math.random() * 5 | 0]; h.style.setProperty("--dx", (Math.random() * 80 - 40) + "px"); $(".lv-stage").appendChild(h); setTimeout(function(){ h.remove(); }, 2300); }
    function send(obj, to){ try { return R.localParticipant.publishData(enc.encode(JSON.stringify(obj)), to ? {reliable: true, destinationIdentities: to} : {reliable: true}); } catch (e) { return Promise.resolve(); } }
    function count(){ $("[data-n]").textContent = R.remoteParticipants.size; }
    function isHost(p){ try { return JSON.parse(p.metadata || "{}").host === 1; } catch (e) { return false; } }
    function layout(){
      var hostP = host ? R.localParticipant : null, guest = null;
      R.remoteParticipants.forEach(function(p){ if (isHost(p)) hostP = p; else if (p.getTrackPublication(LK.Track.Source.Camera) && p.getTrackPublication(LK.Track.Source.Camera).track) guest = guest || p; });
      if (!host && R.localParticipant.isCameraEnabled) guest = R.localParticipant;
      var hv = hostP && hostP.getTrackPublication(LK.Track.Source.Camera), gv = guest && guest.getTrackPublication(LK.Track.Source.Camera);
      if (hv && hv.track){ hv.track.attach(mainV); $("[data-mid]").style.display = "none"; mainV.style.transform = host && facing === "user" ? "scaleX(-1)" : ""; }
      else if (!host && R.state === "connected"){ $("[data-mid]").style.display = ""; $("[data-mid]").innerHTML = "<div><div style='font-size:40px'>📵</div><p>The host's camera is off for a moment…</p></div>"; }
      if (gv && gv.track){ pip.style.display = ""; gv.track.attach(pipV); } else { pip.style.display = "none"; }
      count();
    }
    function over(msg){
      if (ended) return; ended = true; clearInterval(timer); clearInterval(beatT);
      try { R.disconnect(); } catch (e) {}
      (preTracks || []).forEach(function(t){ t.stop(); });
      if (lock) try { lock.release(); } catch (e) {}
      $("[data-mid]").style.display = ""; $("[data-mid]").innerHTML = "<div><div style='font-size:46px'>🎬</div><h2>Live ended</h2><p>" + esc(msg || "Thanks for watching!") + "</p><a class='lv-go' style='text-decoration:none' href='/live'>More lives</a> <a class='lv-pill' style='padding:11px 16px;text-decoration:none' href='/feed'>XpertConnect</a></div>";
      mainV.style.display = "none"; pip.style.display = "none"; $(".lv-bar").style.display = "none"; feed.style.display = "none";
    }
    R.on(LK.RoomEvent.TrackSubscribed, function(track){ if (track.kind === "audio"){ var el = track.attach(); el.setAttribute("data-lva", ""); el.autoplay = true; app.appendChild(el); soundCheck(); } layout(); })
     .on(LK.RoomEvent.TrackUnsubscribed, function(track){ if (track.kind === "audio") track.detach().forEach(function(e){ e.remove(); }); layout(); })
     .on(LK.RoomEvent.AudioPlaybackStatusChanged, soundCheck).on(LK.RoomEvent.LocalTrackPublished, layout).on(LK.RoomEvent.LocalTrackUnpublished, layout)
     .on(LK.RoomEvent.TrackMuted, layout).on(LK.RoomEvent.TrackUnmuted, layout)
     .on(LK.RoomEvent.ParticipantConnected, function(p){ count(); if (host){ say("", p.name + " joined", true); clearTimeout(beatSoon); beatSoon = setTimeout(beatNow, 3000); } })
     .on(LK.RoomEvent.ParticipantDisconnected, function(p){ layout(); if (!host && isHost(p)) setTimeout(function(){ api(L.id + "/").then(function(x){ if (x.live && x.live.status !== "live") over(); }); }, 4000); })
     .on(LK.RoomEvent.Disconnected, function(reason){ if (!ended && LK.DisconnectReason && reason === LK.DisconnectReason.PARTICIPANT_REMOVED) return over("The host removed you from this live."); if (!ended) api(L.id + "/").then(function(x){ if (x.live && x.live.status !== "live") over(); else over("The connection dropped. Reload to watch again."); }); })
     .on(LK.RoomEvent.ParticipantPermissionsChanged, function(prev, p){
        if (p !== R.localParticipant || host) return;
        if (!p.permissions.canPublish){ p.setCameraEnabled(false).catch(function(){}); p.setMicrophoneEnabled(false).catch(function(){}); say("", "You are back in the audience.", true); setTimeout(layout, 300); }
     })
     .on(LK.RoomEvent.DataReceived, function(payload, p){
        var m; try { m = JSON.parse(dec.decode(payload)); } catch (e) { return; }
        var who = (p && p.name) || String(m.n || "").slice(0, 40);
        if (m.t === "c" && m.x) say(who, String(m.x).slice(0, 200));
        if (m.t === "h"){ hearts++; heart(); }
        if (m.t === "inv" && !host && p && isHost(p)) invite();
        if (m.t === "end" && !host) over();
     });
    function invite(){
      var s = sheet('<h3>🎥 ' + esc(L.host.name) + ' invites you on screen</h3><p style="opacity:.85">Your camera and microphone will be live for everyone watching.</p><div class="lv-share"><button class="btn" data-ok>Join on screen</button><button class="btn" style="background:#2A3150" data-no>Not now</button></div>');
      s.querySelector("[data-ok]").onclick = function(){ s.remove(); R.localParticipant.enableCameraAndMicrophone().then(function(){ say("", "You are on screen now.", true); layout(); }).catch(function(e){ toast("Camera could not start: " + (e.message || e.name)); }); };
      s.querySelector("[data-no]").onclick = function(){ s.remove(); send({t: "c", x: "can't join on screen right now"}); };
    }
    function sheet(html){ var ov = D.createElement("div"); ov.className = "lv-sh"; ov.innerHTML = '<div class="lv-box">' + html + "</div>"; ov.addEventListener("click", function(e){ if (e.target === ov) ov.remove(); }); B.appendChild(ov); return ov; }
    function viewers(){
      var rows = [];
      R.remoteParticipants.forEach(function(p){
        var on = !!(p.getTrackPublication(LK.Track.Source.Camera) && p.getTrackPublication(LK.Track.Source.Camera).track);
        rows.push('<div class="lv-row"><span>' + esc(p.name || "Guest") + (on ? " 🎥" : "") + "</span>"
          + (host && /^u\d+$/.test(p.identity) ? (on ? '<button class="g" data-off="' + esc(p.identity) + '">Off screen</button>' : '<button data-inv="' + esc(p.identity) + '">Invite on screen</button>') : "")
          + (host ? '<button class="r" data-rm="' + esc(p.identity) + '">Remove</button>' : "") + "</div>");
      });
      var s = sheet("<h3>👁 Watching (" + R.remoteParticipants.size + ")</h3>" + (rows.join("") || "<p style='opacity:.8'>No viewers yet. Share your live!</p>")
        + '<div class="lv-share" style="margin-top:12px"><button class="btn" data-sh>↗️ Share the live</button></div>');
      s.addEventListener("click", function(e){
        var b = e.target.closest("button"); if (!b) return;
        if (b.hasAttribute("data-sh")){ share(); return; }
        var id = b.getAttribute("data-inv") || b.getAttribute("data-off") || b.getAttribute("data-rm"); if (!id) return;
        b.disabled = true;
        if (b.hasAttribute("data-inv")) api(L.id + "/stage/", {identity: id, on: true}).then(function(x){ if (!x._ok){ toast(x.detail || "Could not invite."); return; } send({t: "inv"}, [id]); toast("Invitation sent"); s.remove(); });
        if (b.hasAttribute("data-off")) api(L.id + "/stage/", {identity: id, on: false}).then(function(x){ toast(x._ok ? "Taken off screen" : (x.detail || "Could not.")); s.remove(); setTimeout(layout, 800); });
        if (b.hasAttribute("data-rm")) api(L.id + "/block/", {identity: id}).then(function(x){ toast(x._ok ? "Removed from your live" : (x.detail || "Could not.")); s.remove(); });
      });
    }
    function share(){
      var url = location.origin + "/live?id=" + L.id, text = "🔴 " + L.host.name + " is live on XpertCreation: " + L.title;
      if (navigator.share) navigator.share({title: L.title, text: text, url: url}).catch(function(){});
      else sheet('<h3>Share the live</h3><div class="lv-share"><a class="btn" style="text-decoration:none;background:#16A34A" target="_blank" rel="noopener" href="https://wa.me/?text=' + encodeURIComponent(text + " " + url) + '">WhatsApp</a><button class="btn" data-cp>Copy link</button></div>').querySelector("[data-cp]").onclick = function(){ navigator.clipboard && navigator.clipboard.writeText(url); toast("Link copied"); };
    }
    $("[data-eye]").onclick = viewers;
    $("[data-x]").onclick = function(){ if (host && !ended) endLive(); else { over(); location.href = "/live"; } };
    function endLive(){
      var s = sheet('<h3>End your live?</h3><p style="opacity:.85">Everyone watching will see that the live has ended.</p><div class="lv-share"><button class="btn" style="background:#E11D48" data-y>End live</button><button class="btn" style="background:#2A3150" data-n>Keep going</button></div>');
      s.querySelector("[data-n]").onclick = function(){ s.remove(); };
      s.querySelector("[data-y]").onclick = function(){ s.remove(); beatNow().then(function(){ return send({t: "end"}); }).then(function(){ return api(L.id + "/end/", {}); }).then(function(x){ var l2 = x.live || L; over("You were live for " + clock(l2.seconds) + " · " + l2.peak + " watching at most · " + hearts + " hearts"); }); };
    }
    var sayBox = $("[data-say]");
    function post(){ var v = sayBox.value.trim(); if (!v) return; sayBox.value = ""; var nm = me.name || (host ? L.host.name : "You"); send({t: "c", x: v.slice(0, 200), n: nm}); say(nm, v); }
    if (sayBox){ $("[data-send]").onclick = post; sayBox.addEventListener("keydown", function(e){ if (e.key === "Enter"){ e.preventDefault(); post(); } }); }
    if (!host){
      var lastH = 0;
      $("[data-heart]").onclick = function(){ heart(); var n = Date.now(); if (n - lastH > 300){ lastH = n; send({t: "h"}); } };
      $("[data-share]").onclick = share;
    } else {
      $("[data-end]").onclick = endLive;
      $("[data-flip]").onclick = function(){
        facing = facing === "user" ? "environment" : "user";
        var pub = R.localParticipant.getTrackPublication(LK.Track.Source.Camera);
        if (pub && pub.track) pub.track.restartTrack({facingMode: facing}).then(layout).catch(function(){ toast("Could not switch camera"); });
      };
      $("[data-mic]").onclick = function(){ var b = this, on = !R.localParticipant.isMicrophoneEnabled; R.localParticipant.setMicrophoneEnabled(on).then(function(){ b.classList.toggle("off", !on); b.textContent = on ? "🎙️" : "🔇"; }); };
    }
    var beatSoon = null;
    function beatNow(){ if (host && !ended) return api(L.id + "/beat/", {viewers: R.remoteParticipants.size, hearts: hearts}).then(function(x){ if (x._s === 410) over(); }); return Promise.resolve(); }
    var beatT = setInterval(beatNow, 20000);
    R.connect(d.ws, d.token).then(function(){
      $("[data-mid]").style.display = host ? "none" : "";
      if (!host) $("[data-mid]").innerHTML = "<div><div style='font-size:40px'>⏳</div><p>Waiting for the video…</p></div>";
      if (host){
        var opts = {simulcast: true, videoEncoding: {maxBitrate: 1200000, maxFramerate: 24}, videoSimulcastLayers: [LK.VideoPresets.h180, LK.VideoPresets.h360], dtx: true, red: true};
        var ps = (preTracks && preTracks.length ? preTracks : []).map(function(t){ return R.localParticipant.publishTrack(t, t.kind === "video" ? opts : {}); });
        return Promise.all(ps.length ? ps : [R.localParticipant.enableCameraAndMicrophone()]).then(function(){
          if (micOn === false) R.localParticipant.setMicrophoneEnabled(false);
          say("", "You are live! Share the link so people can join.", true); layout();
          if (navigator.wakeLock) navigator.wakeLock.request("screen").then(function(l){ lock = l; }).catch(function(){});
        });
      }
      say("", "Welcome! Be kind in the comments.", true);
      layout(); soundCheck();
    }).catch(function(e){ over("Could not connect to the live (" + (e.message || "network") + "). Check your internet and reload."); });
    window.addEventListener("beforeunload", function(){ try { R.disconnect(); } catch (e) {} });
    window.XLROOM = R;
  }

  function watch(id){
    app.innerHTML = '<div class="lv-stage"><div class="lv-mid"><div><div style="font-size:40px">⏳</div><p>Opening the live…</p></div></div></div>';
    api(id + "/").then(function(d){
      if (!d._ok){ app.innerHTML = '<div class="lv-stage"><div class="lv-mid"><div><div style="font-size:46px">🚫</div><h2>' + esc(d.detail || "Not found") + '</h2><a class="lv-go" style="text-decoration:none" href="/live">See who is live</a></div></div></div>'; return; }
      if (d.live.status !== "live" || !d.token){
        app.innerHTML = '<div class="lv-stage"><div class="lv-mid"><div><div style="font-size:46px">🎬</div><h2>This live has ended</h2><p>' + esc(d.live.host.name) + " · " + esc(d.live.title) + '</p><a class="lv-go" style="text-decoration:none" href="/live">See who is live now</a></div></div></div>'; return;
      }
      room(d, null, "user", true);
    });
  }

  var id = +Q.get("id");
  if (id) watch(id); else if (Q.get("go")) prep(); else list();
})();
