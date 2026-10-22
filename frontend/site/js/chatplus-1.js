/* XpertChat plus (chatplus-1.js)
   - message box like WhatsApp: one rounded box with emoji, attach and camera inside, one round mic / send button
   - attach menu: Document, Gallery, Camera, Location, Contact, Poll, Event, Quick reply
   - cards in the chat for polls (live votes), events (your time + times around the world + calendar), locations and contacts */
(function(){
  "use strict";
  if (window.XCPLUS) return;
  var PAGE = /^\/group\/\d+/.test(location.pathname) ? "group" : /^\/chat/.test(location.pathname) ? "chat" : "";
  if (!PAGE) return;
  var D = document, B = D.body;
  function $(id){ return D.getElementById(id); }
  function esc(s){ return String(s == null ? "" : s).replace(/[&<>"']/g, function(c){ return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]; }); }
  function ck(n){ var m = D.cookie.match(new RegExp("(?:^|; )" + n + "=([^;]*)")); return m ? decodeURIComponent(m[1]) : ""; }
  function jfetch(url, body){
    var o = {method: body === undefined ? "GET" : "POST", credentials: "same-origin", headers: {"Accept": "application/json"}};
    if (body !== undefined){ o.headers["Content-Type"] = "application/json"; o.headers["X-CSRFToken"] = ck("xc_csrf") || ck("csrftoken"); o.body = JSON.stringify(body); }
    return fetch(url, o).then(function(r){ return r.json().catch(function(){ return {}; }).then(function(d){ if (!r.ok) throw new Error(d.detail || "Error " + r.status); return d; }); });
  }
  function toast(t){ var d = D.createElement("div"); d.className = "xpt"; d.textContent = t; B.appendChild(d); setTimeout(function(){ d.remove(); }, 2800); }
  var IC = {
    doc: '<svg viewBox="0 0 24 24" width="26" height="26" fill="#7F66FF"><path d="M6 2h8l6 6v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2zm7 1.5V9h5.5zM8 13h8v1.6H8zm0 3.4h8V18H8z"/></svg>',
    gal: '<svg viewBox="0 0 24 24" width="26" height="26" fill="#007BFC"><path d="M20 4H8a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zm-1 11H9l2.6-3.4 1.8 2.3 2.6-3.3zM4 8H2v12a2 2 0 0 0 2 2h12v-2H4z"/></svg>',
    cam: '<svg viewBox="0 0 24 24" width="26" height="26" fill="#FF2E74"><path d="M9 3 7.2 5H4a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-3.2L15 3zm3 14.5a5 5 0 1 1 0-10 5 5 0 0 1 0 10zm0-2a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"/></svg>',
    loc: '<svg viewBox="0 0 24 24" width="26" height="26" fill="#1DA851"><path d="M12 2a7 7 0 0 0-7 7c0 5.2 7 13 7 13s7-7.8 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z"/></svg>',
    con: '<svg viewBox="0 0 24 24" width="26" height="26" fill="#009DE2"><path d="M12 12a5 5 0 1 0 0-10 5 5 0 0 0 0 10zm0 2c-4.4 0-8 2.2-8 5v3h16v-3c0-2.8-3.6-5-8-5z"/></svg>',
    poll: '<svg viewBox="0 0 24 24" width="26" height="26" fill="#FFB938"><rect x="3" y="4" width="14" height="3.4" rx="1.7"/><rect x="3" y="10.3" width="18" height="3.4" rx="1.7"/><rect x="3" y="16.6" width="9" height="3.4" rx="1.7"/></svg>',
    ev: '<svg viewBox="0 0 24 24" width="26" height="26" fill="#FF2E74"><path d="M7 2v2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-2V2h-2v2H9V2zM5 9h14v11H5zm2 2v4h4v-4z"/></svg>',
    quick: '<svg viewBox="0 0 24 24" width="26" height="26" fill="#F5A623"><path d="M13 2 4 14h6l-1 8 9-12h-6z"/></svg>',
    clip: '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.5 11.5l-8.2 8.2a5 5 0 0 1-7.1-7.1l8.5-8.5a3.4 3.4 0 0 1 4.8 4.8l-8.4 8.4a1.7 1.7 0 0 1-2.4-2.4l7.7-7.7"/></svg>',
    camo: '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M4 7h3l2-2.5h6L17 7h3a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1z"/><circle cx="12" cy="12.5" r="3.6"/></svg>'
  };

  /* ------------------------------------------------------------ styles */
  var st = D.createElement("style");
  st.textContent = ""
   + ".xpbar{display:flex!important;align-items:flex-end!important;gap:8px!important;padding:6px 8px calc(6px + env(safe-area-inset-bottom))!important;background:transparent!important;border:0!important}"
   + ".xppill{flex:1;min-width:0;display:flex;align-items:flex-end;gap:0;background:var(--card,#fff);border-radius:26px;box-shadow:0 1px 3px rgba(0,0,0,.14);padding:3px 4px;border:1px solid var(--line,#e6e9ef)}"
   + ".xppill>textarea{text-align:left!important;flex:1;min-width:0;border:0!important;background:transparent!important;box-shadow:none!important;outline:none!important;resize:none;padding:11px 6px!important;margin:0!important;font:inherit;font-size:16px;line-height:1.35;min-height:44px!important;height:44px;max-height:140px;overflow-y:auto;color:inherit;border-radius:0!important}"
   + ".xppill>.att3,.xppill>label,.xppill>button,.xppill>.xccam{width:42px!important;height:42px!important;flex:0 0 42px!important;margin:1px 0!important;border-radius:50%!important;border:0!important;background:transparent!important;box-shadow:none!important;color:var(--ink-soft,#54656f)!important;display:grid!important;place-items:center!important;padding:0!important;align-self:flex-end!important;font-size:20px}"
   + ".xppill>*:hover{background:rgba(127,127,127,.1)!important}"
   + "html body .xppill>.xccam{display:none!important}"
   + "html body .xpbar>#csend,html body .xpbar>#cmic,html body .xpbar>#gsend,html body .xpbar>#gmic{width:50px!important;height:50px!important;flex:0 0 50px!important;border-radius:50%!important;border:0!important;background:#0f9d58!important;background-image:none!important;color:#fff!important;display:grid!important;place-items:center!important;box-shadow:0 2px 6px rgba(15,157,88,.35)!important;padding:0!important;align-self:flex-end!important;font-size:20px}"
   + ".xpbar>#csend svg,.xpbar>#cmic svg{stroke:#fff}.xpbar>#cmic svg{fill:none}"
   + "html body .xpbar.xpempty>#csend,html body .xpbar.xpempty>#gsend{display:none!important}html body .xpbar:not(.xpempty)>#cmic,html body .xpbar:not(.xpempty)>#gmic{display:none!important}"
   + ".xpbar>.xccam{display:none!important}"
   + ".xpsh{position:fixed;inset:0;z-index:2147481000;background:rgba(0,0,0,.35);display:flex;align-items:flex-end;justify-content:center;animation:xpf .15s}"
   + "@keyframes xpf{from{opacity:0}to{opacity:1}}"
   + ".xpbox{width:100%;max-width:520px;max-height:90vh;overflow:auto;background:var(--card,#fff);color:var(--ink,#111b21);border-radius:22px 22px 0 0;padding:10px 16px calc(18px + env(safe-area-inset-bottom));box-shadow:0 -4px 24px rgba(0,0,0,.15);animation:xpu .2s ease-out}"
   + "@keyframes xpu{from{transform:translateY(40px)}to{transform:none}}"
   + "@media(min-width:700px){.xpsh{align-items:center}.xpbox{border-radius:20px}}"
   + ".xpgrab{width:40px;height:5px;border-radius:3px;background:rgba(127,127,127,.35);margin:2px auto 12px}"
   + ".xpgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px 6px;padding:4px 0 6px}"
   + ".xpgo{display:flex;flex-direction:column;align-items:center;gap:7px;border:0;background:transparent;color:inherit;font:inherit;font-size:13px;cursor:pointer;padding:0}"
   + ".xpgo i{width:62px;height:62px;border-radius:50%;display:grid;place-items:center;border:1px solid var(--line,#e9edef);background:var(--card,#fff)}"
   + ".xpgo:active i{transform:scale(.94)}"
   + ".xpbox h3{margin:2px 0 12px;font-size:18px;display:flex;justify-content:space-between;align-items:center}.xpx{border:0;background:transparent;font-size:22px;cursor:pointer;color:inherit}"
   + ".xpbox input[type=text],.xpbox input[type=datetime-local],.xpbox textarea{width:100%;box-sizing:border-box;border:1px solid var(--line,#d1d7db);border-radius:12px;padding:11px 12px;font:inherit;font-size:15px;background:transparent;color:inherit;margin:4px 0 8px}"
   + ".xpbox label.l{display:block;font-size:13px;font-weight:600;margin-top:6px;color:var(--ink-soft,#54656f)}"
   + ".xpbtn{border:0;border-radius:22px;padding:11px 20px;font:inherit;font-weight:700;cursor:pointer;background:#0f9d58;color:#fff}.xpbtn.o{background:transparent;color:inherit;border:1px solid var(--line,#d1d7db)}"
   + ".xprow{display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap;margin-top:10px}.xper{color:#d93025;font-size:13px;min-height:1em}"
   + ".xpli{display:flex;align-items:center;gap:12px;padding:10px 4px;border-bottom:1px solid var(--line,#eef0f2);cursor:pointer;border-left:0;border-right:0;border-top:0;background:transparent;width:100%;text-align:left;font:inherit;color:inherit}"
   + ".xpav{width:42px;height:42px;border-radius:50%;background:#dfe5e7 center/cover;display:grid;place-items:center;font-weight:700;color:#54656f;flex:0 0 42px}"
   + ".xpt{position:fixed;left:50%;bottom:96px;transform:translateX(-50%);background:#111b21;color:#fff;padding:9px 16px;border-radius:20px;z-index:2147481500;font-size:14px}"
   /* cards */
   + ".xpc{border-radius:12px;background:rgba(127,127,127,.07);padding:10px 12px;margin:2px 0 4px;min-width:220px;max-width:300px;white-space:normal}"
   + ".xpc b.t{display:block;font-size:15px;margin-bottom:6px}.xpc .s{font-size:12.5px;opacity:.75}"
   + ".xpo{position:relative;display:block;width:100%;text-align:left;border:1px solid var(--line,#d1d7db);background:transparent;border-radius:10px;padding:9px 10px;margin:6px 0;font:inherit;font-size:14px;cursor:pointer;overflow:hidden;color:inherit}"
   + ".xpo i{position:absolute;left:0;top:0;bottom:0;background:rgba(15,157,88,.16);z-index:0;transition:width .3s}.xpo span{position:relative;z-index:1;display:flex;justify-content:space-between;gap:8px}.xpo.mine{border-color:#0f9d58}.xpo.mine span b:before{content:'\\2714 ';color:#0f9d58}"
   + ".xpmap{position:relative;display:block;width:100%;height:150px;border-radius:10px;overflow:hidden;background:#e5e3df center/cover;margin-bottom:6px}.xpmap .pin{position:absolute;width:30px;height:30px;transform:translate(-50%,-100%);font-size:28px;line-height:30px;text-align:center}"
   + ".xpmap small{position:absolute;right:4px;bottom:2px;font-size:9px;background:rgba(255,255,255,.75);padding:0 3px;border-radius:3px;color:#333}"
   + ".xpca{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}.xpca a,.xpca button{border:1px solid var(--line,#d1d7db);background:transparent;border-radius:16px;padding:6px 11px;font:inherit;font-size:13px;cursor:pointer;color:inherit;text-decoration:none}"
   + ".xptz{display:grid;grid-template-columns:1fr 1fr;gap:3px 10px;font-size:12px;margin-top:6px}";
  D.head.appendChild(st);

  /* ------------------------------------------------------------ the message box */
  var EL = PAGE === "chat"
    ? {row: function(){ return $("reply4"); }, ta: function(){ return $("cinput"); }, emo: function(){ var r = $("reply4"); return r && r.querySelector("[data-emo3]"); }, att: function(){ var i = $("cphoto"); return i && i.closest("label"); }, file: function(){ return $("cphoto"); }, mic: "cmic", send: "csend"}
    : {row: function(){ return $("gform"); }, ta: function(){ return $("gq"); }, emo: function(){ return $("xcgstk"); }, att: function(){ var i = $("gfile"); return i && i.closest("label"); }, file: function(){ return $("gfile"); }, mic: "gmic", send: "gsend"};
  function build(){
    var row = EL.row(), ta = EL.ta(); if (!row || !ta) return;
    var pill = row.querySelector(".xppill");
    if (!pill){
      row.classList.add("xpbar");
      pill = D.createElement("div"); pill.className = "xppill";
      row.insertBefore(pill, ta); pill.appendChild(ta); ta.rows = 1; grow(ta);
    }
    var emo = EL.emo(); if (emo && emo.parentNode !== pill) pill.insertBefore(emo, pill.firstChild);
    var att = EL.att();
    if (att && att.parentNode !== pill){ pill.appendChild(att); att.innerHTML = att.innerHTML.replace(/^[\s\S]*?(<input)/, IC.clip + "$1").replace(/^📎/, ""); att.title = "Attach"; att.setAttribute("aria-label", "Attach"); }
    if (!pill.querySelector(".xpcam")){
      var cb = D.createElement("button"); cb.type = "button"; cb.className = "xpcam"; cb.setAttribute("aria-label", "Camera"); cb.innerHTML = IC.camo;
      cb.addEventListener("click", function(e){ e.preventDefault(); openCam(); });
      pill.appendChild(cb);
    }
    var mic = $(EL.mic), send = $(EL.send);
    if (mic && mic.parentNode !== row) row.appendChild(mic);
    if (send && send.parentNode !== row) row.appendChild(send);
    if (send && mic && send.previousElementSibling !== mic) row.appendChild(send);
    row.classList.toggle("xpempty", !!mic && !ta.value.trim());
  }
  setInterval(build, 700);
  function grow(ta){ ta.style.setProperty("height", "44px", "important"); ta.style.setProperty("height", Math.min(140, Math.max(44, ta.scrollHeight)) + "px", "important"); }
  D.addEventListener("input", function(e){ var ta = EL.ta(); if (e.target === ta){ grow(ta); var row = EL.row(); if (row) row.classList.toggle("xpempty", !!$(EL.mic) && !ta.value.trim()); } });
  setInterval(function(){ var ta = EL.ta(), row = EL.row(); if (ta && row){ row.classList.toggle("xpempty", !!$(EL.mic) && !ta.value.trim()); if (!ta.value) grow(ta); } }, 400);
  // the attach button opens our menu instead of the file picker
  D.addEventListener("click", function(e){
    var att = EL.att(); if (!att || !att.contains(e.target) || e.target === EL.file()) return;
    e.preventDefault(); e.stopPropagation(); menu();
  }, true);

  /* ------------------------------------------------------------ sending */
  function curThread(){ var c = window.XC3 && XC3.cur && XC3.cur(); return c && c.id; }
  function sendText(body){
    if (PAGE === "group"){ if (!window.XCG) return Promise.reject(new Error("Open the group first.")); XCG.send(body); return Promise.resolve(); }
    var ta = $("cinput"), sb = $("csend"); if (!ta || !sb) return Promise.reject(new Error("Open a chat first."));
    var keep = ta.value; ta.value = body; ta.dispatchEvent(new Event("input", {bubbles: true})); sb.click();
    setTimeout(function(){ if (!ta.value && keep) ta.value = keep; }, 50);
    return Promise.resolve();
  }
  function sendFile(file){
    if (PAGE === "group"){ if (!window.XCG) return Promise.reject(new Error("Open the group first.")); XCG.send("", file); return Promise.resolve(); }
    var id = curThread(); if (!id) return Promise.reject(new Error("Open a chat first."));
    var fd = new FormData(); fd.append(/^image\//.test(file.type) ? "photo" : "file", file);
    return fetch("/api/notify/threads/" + id + "/", {method: "POST", credentials: "same-origin", headers: {"X-CSRFToken": ck("xc_csrf")}, body: fd})
      .then(function(r){ return r.json().catch(function(){ return {}; }).then(function(d){ if (!r.ok) throw new Error(d.detail || (r.status === 413 ? "That is too big (8 MB at most)." : "Could not send it.")); if (d.message && XC3.add) XC3.add([d.message]); }); });
  }
  function openCam(opts){
    if (!window.XCAM){ toast("The camera is loading, try again in a moment."); return; }
    XCAM.open(Object.assign({onSend: function(f){ return sendFile(f); }}, opts || {}));
  }

  /* ------------------------------------------------------------ sheets */
  function sheet(html){
    var ov = D.createElement("div"); ov.className = "xpsh"; ov.innerHTML = '<div class="xpbox"><div class="xpgrab"></div>' + html + "</div>";
    ov.addEventListener("click", function(e){ if (e.target === ov || e.target.closest("[data-xpx]")) ov.remove(); });
    B.appendChild(ov); return ov;
  }
  function menu(){
    var items = [["doc", "Document", IC.doc], ["gal", "Gallery", IC.gal], ["cam", "Camera", IC.cam], ["loc", "Location", IC.loc], ["con", "Contact", IC.con], ["poll", "Poll", IC.poll], ["ev", "Event", IC.ev], ["quick", "Quick reply", IC.quick]];
    var ov = sheet('<div class="xpgrid">' + items.map(function(i){ return '<button class="xpgo" data-go="' + i[0] + '"><i>' + i[2] + "</i>" + i[1] + "</button>"; }).join("") + "</div>");
    ov.addEventListener("click", function(e){
      var b = e.target.closest("[data-go]"); if (!b) return; var k = b.dataset.go; ov.remove();
      if (k === "doc"){ var f = EL.file(); if (f){ f.setAttribute("accept", ".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv"); f.click(); setTimeout(function(){ f.setAttribute("accept", "image/*,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv"); }, 1500); } }
      else if (k === "gal") gallery();
      else if (k === "cam") openCam();
      else if (k === "loc") location_();
      else if (k === "con") contact();
      else if (k === "poll") poll();
      else if (k === "ev") event_();
      else if (k === "quick") quick();
    });
  }
  function gallery(){
    var inp = D.createElement("input"); inp.type = "file"; inp.accept = "image/*,video/*"; inp.style.display = "none"; B.appendChild(inp);
    inp.addEventListener("change", function(){
      var f = inp.files[0]; inp.remove(); if (!f) return;
      if (/^video\//.test(f.type)){
        if (f.size > 7.5 * 1048576) return toast("That video is over 8 MB. Record a shorter clip with the camera.");
        if (!/\.(mp4|webm|mov)$/i.test(f.name)) f = new File([f], "video.mp4", {type: f.type});
        return sendFile(f).then(function(){ toast("Sent"); }, function(e){ toast(e.message); });
      }
      var url = URL.createObjectURL(f);
      var ov = sheet('<h3>Send photo <button class="xpx" data-xpx>✕</button></h3><img src="' + url + '" alt="" style="width:100%;max-height:50vh;object-fit:contain;border-radius:12px;background:#000"><div class="xprow"><button class="xpbtn o" data-f>✨ Add filter</button><button class="xpbtn" data-s>➤ Send</button></div>');
      ov.addEventListener("click", function(e){
        if (e.target.closest("[data-s]")){ ov.remove(); sendFile(f).catch(function(x){ toast(x.message); }); }
        if (e.target.closest("[data-f]")){ ov.remove(); if (window.XCAM) XCAM.edit(f, {onSend: function(x){ return sendFile(x); }}); }
      });
    });
    inp.click();
  }
  function location_(){
    var ov = sheet('<h3>📍 Send location <button class="xpx" data-xpx>✕</button></h3><p class="s" style="opacity:.75;margin:0 0 10px">Your phone asks first. Only this one place is sent, nothing keeps tracking you.</p><div class="xprow" style="justify-content:stretch"><button class="xpbtn" data-here style="flex:1">📍 Send my current location</button></div><p class="xper"></p>');
    ov.querySelector("[data-here]").addEventListener("click", function(){
      var b = this, er = ov.querySelector(".xper");
      if (!navigator.geolocation){ er.textContent = "This phone can't share its location here."; return; }
      b.disabled = true; b.textContent = "Finding you…";
      navigator.geolocation.getCurrentPosition(function(p){
        var la = p.coords.latitude.toFixed(5), lo = p.coords.longitude.toFixed(5);
        ov.remove(); sendText("[loc] 📍 Location\nhttps://www.openstreetmap.org/?mlat=" + la + "&mlon=" + lo + "#map=17/" + la + "/" + lo);
      }, function(e){ b.disabled = false; b.textContent = "📍 Send my current location"; er.textContent = e.code === 1 ? "Location is off for this site. Allow it in your browser settings and try again." : "Could not find your location. Try again outside or with GPS on."; }, {enableHighAccuracy: true, timeout: 15000, maximumAge: 30000});
    });
  }
  function contact(){
    var ov = sheet('<h3>👤 Send a contact <button class="xpx" data-xpx>✕</button></h3><input type="text" placeholder="Search your connections" data-q><div data-list><p class="s" style="opacity:.7">Loading…</p></div>');
    var people = [], draw = function(){
      var q = ov.querySelector("[data-q]").value.trim().toLowerCase();
      var list = people.filter(function(p){ return !q || (p.name || "").toLowerCase().indexOf(q) > -1; }).slice(0, 60);
      ov.querySelector("[data-list]").innerHTML = list.length ? list.map(function(p){ return '<button class="xpli" data-slug="' + esc(p.slug || "") + '" data-name="' + esc(p.name) + '"><span class="xpav"' + (p.avatar_url ? ' style="background-image:url(\'' + esc(p.avatar_url) + '\')"' : "") + ">" + (p.avatar_url ? "" : esc((p.name || "?").charAt(0))) + "</span><span><b>" + esc(p.name) + "</b><br><small style=\"opacity:.7\">" + esc(p.headline || "") + "</small></span></button>"; }).join("") : '<p class="s" style="opacity:.7">No connections found.</p>';
    };
    jfetch("/api/network/me/people/connections/").then(function(d){ people = (d.people || []).filter(function(p){ return p.slug; }); draw(); }).catch(function(){ ov.querySelector("[data-list]").innerHTML = '<p class="xper">Could not load your connections.</p>'; });
    ov.querySelector("[data-q]").addEventListener("input", draw);
    ov.addEventListener("click", function(e){ var b = e.target.closest("[data-slug]"); if (!b) return; ov.remove();
      sendText("[contact:" + b.dataset.slug + "] 👤 " + b.dataset.name + "\nhttps://xpertcreation.com/in/" + b.dataset.slug); });
  }
  function poll(){
    var ov = sheet('<h3>📊 Create poll <button class="xpx" data-xpx>✕</button></h3><label class="l">Question</label><input type="text" maxlength="200" data-q placeholder="Ask something"><label class="l">Options</label><div data-opts></div>'
      + '<button class="xpbtn o" data-add style="padding:7px 14px">+ Add option</button><label style="display:flex;gap:8px;align-items:center;margin-top:12px"><input type="checkbox" data-multi> Allow more than one answer</label><p class="xper"></p><div class="xprow"><button class="xpbtn" data-send>➤ Send poll</button></div>');
    var box = ov.querySelector("[data-opts]"), add = function(){ if (box.children.length >= 12) return; var i = D.createElement("input"); i.type = "text"; i.maxLength = 80; i.placeholder = "Option " + (box.children.length + 1); box.appendChild(i); };
    add(); add(); ov.querySelector("[data-q]").focus();
    ov.querySelector("[data-add]").addEventListener("click", add);
    box.addEventListener("input", function(e){ if (e.target === box.lastElementChild && e.target.value) add(); });
    ov.querySelector("[data-send]").addEventListener("click", function(){
      var b = this, er = ov.querySelector(".xper"), q = ov.querySelector("[data-q]").value.trim(), opts = [].map.call(box.children, function(i){ return i.value.trim(); }).filter(Boolean);
      if (!q){ er.textContent = "Write the question."; return; } if (opts.length < 2){ er.textContent = "Add at least two options."; return; }
      var where = PAGE === "group" ? {group: +(window.XCG && XCG.gid())} : {thread: curThread()};
      b.disabled = true;
      jfetch("/api/polls/", Object.assign({question: q, options: opts, multi: ov.querySelector("[data-multi]").checked}, where)).then(function(p){ ov.remove(); sendText("[poll:" + p.id + "] 📊 Poll: " + q); })
        .catch(function(x){ b.disabled = false; er.textContent = x.message; });
    });
  }
  function event_(){
    var ov = sheet('<h3>📅 Create event <button class="xpx" data-xpx>✕</button></h3><label class="l">Event name</label><input type="text" maxlength="100" data-t placeholder="e.g. Team meeting, Iftar party"><label class="l">Date and time (your time, ' + esc(zone()) + ')</label><input type="datetime-local" data-w>'
      + '<label class="l">Place or link (optional)</label><input type="text" maxlength="150" data-p placeholder="Address, or a meeting link"><label class="l">Note (optional)</label><textarea rows="2" maxlength="300" data-n></textarea><p class="xper"></p><div class="xprow"><button class="xpbtn" data-send>➤ Send event</button></div>');
    ov.querySelector("[data-send]").addEventListener("click", function(){
      var er = ov.querySelector(".xper"), t = ov.querySelector("[data-t]").value.trim(), w = ov.querySelector("[data-w]").value, p = ov.querySelector("[data-p]").value.trim(), n = ov.querySelector("[data-n]").value.trim();
      if (!t){ er.textContent = "Give the event a name."; return; } if (!w){ er.textContent = "Pick the date and time."; return; }
      var d = new Date(w); if (isNaN(d)){ er.textContent = "That date is not valid."; return; }
      ov.remove();
      sendText("[event:" + d.toISOString() + "] 📅 " + t.replace(/\n/g, " ") + (p ? "\n📍 " + p.replace(/\n/g, " ") : "") + (n ? "\n" + n : ""));
    });
  }
  function quick(){
    var list = []; try { list = JSON.parse(localStorage.getItem("xc_quick") || "[]"); } catch (e) {}
    if (!list.length) list = ["Assalam o alaikum! How can I help you?", "Thank you for your message. I will reply soon.", "Please send your location and phone number.", "Your order has been sent. Thank you!"];
    var save = function(){ try { localStorage.setItem("xc_quick", JSON.stringify(list)); } catch (e) {} };
    var ov = sheet("");
    var draw = function(){
      ov.firstChild.innerHTML = '<div class="xpgrab"></div><h3>⚡ Quick replies <button class="xpx" data-xpx>✕</button></h3><p class="s" style="opacity:.7;margin:0 0 6px">Tap one to put it in the message box. Saved on this phone.</p>'
        + list.map(function(t, i){ return '<div style="display:flex;align-items:center;gap:6px"><button class="xpli" data-use="' + i + '" style="flex:1">' + esc(t) + '</button><button class="xpx" data-del="' + i + '" aria-label="Remove" style="font-size:18px">🗑</button></div>'; }).join("")
        + '<label class="l" style="margin-top:12px">New quick reply</label><textarea rows="2" maxlength="500" data-new></textarea><div class="xprow"><button class="xpbtn o" data-add>+ Save</button></div>';
    };
    draw();
    ov.addEventListener("click", function(e){
      var u = e.target.closest("[data-use]"), d = e.target.closest("[data-del]"), a = e.target.closest("[data-add]");
      if (u){ var ta = EL.ta(); if (ta){ ta.value = list[+u.dataset.use]; ta.dispatchEvent(new Event("input", {bubbles: true})); ta.focus(); } ov.remove(); }
      if (d){ list.splice(+d.dataset.del, 1); save(); draw(); }
      if (a){ var v = ov.querySelector("[data-new]").value.trim(); if (v){ list.unshift(v); list = list.slice(0, 30); save(); draw(); } }
    });
  }

  /* ------------------------------------------------------------ cards in the chat */
  var ZONES = [["🇵🇰 Pakistan", "Asia/Karachi"], ["🇮🇳 India", "Asia/Kolkata"], ["🇦🇪 UAE", "Asia/Dubai"], ["🇸🇦 Saudi Arabia", "Asia/Riyadh"], ["🇬🇧 UK", "Europe/London"], ["🇩🇪 Germany", "Europe/Berlin"], ["🇺🇸 New York", "America/New_York"], ["🇺🇸 Los Angeles", "America/Los_Angeles"], ["🇨🇦 Toronto", "America/Toronto"], ["🇦🇺 Sydney", "Australia/Sydney"]];
  function zone(){ try { return Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Karachi"; } catch (e) { return "Asia/Karachi"; } }
  function when(d, tz){ return new Intl.DateTimeFormat("en-GB", {timeZone: tz, weekday: "short", day: "numeric", month: "short", hour: "numeric", minute: "2-digit", hour12: true}).format(d); }
  function ics(title, d, place, note){
    var f = function(x){ return x.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, ""); }, e = new Date(d.getTime() + 3600000);
    var t = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//XpertCreation//XpertChat//EN", "BEGIN:VEVENT", "UID:" + f(d) + "-" + Math.random().toString(36).slice(2) + "@xpertcreation.com", "DTSTAMP:" + f(new Date()), "DTSTART:" + f(d), "DTEND:" + f(e),
      "SUMMARY:" + title.replace(/[\n,;]/g, " "), place ? "LOCATION:" + place.replace(/[\n,;]/g, " ") : "", note ? "DESCRIPTION:" + note.replace(/[\n,;]/g, " ") : "", "END:VEVENT", "END:VCALENDAR"].filter(Boolean).join("\r\n");
    var a = D.createElement("a"); a.href = URL.createObjectURL(new Blob([t], {type: "text/calendar"})); a.download = "event.ics"; B.appendChild(a); a.click(); setTimeout(function(){ a.remove(); }, 400);
  }
  var BUB = PAGE === "chat" ? ".msg8[data-mid]" : ".gm[data-mid]";
  function bodyOf(el){
    var host = el.querySelector(".cb");
    var nodes = host ? [].slice.call(host.childNodes) : [].slice.call(el.childNodes).filter(function(n){ return n.nodeType === 3 || (n.nodeType === 1 && /^(A|BR|SPAN|B|I|EM|STRONG)$/.test(n.tagName) && !/\b(who|xrtag|xcfw)\b/.test(n.className || "")); });
    nodes = nodes.filter(function(n){ return !(n.nodeType === 1 && /\b(xcq|xcfw)\b/.test(n.className || "")); });
    var text = nodes.map(function(n){ return n.nodeType === 1 && n.tagName === "BR" ? "\n" : n.textContent; }).join("");
    return {host: host || el, nodes: nodes, text: text};
  }
  function place(el, b, card){ b.nodes.forEach(function(n){ n.parentNode && n.parentNode.removeChild(n); }); var sm = b.host === el ? el.querySelector(":scope > small") : null; var w = D.createElement("div"); w.innerHTML = card; var c = w.firstChild; if (sm) el.insertBefore(c, sm); else b.host.appendChild(c); return c; }
  var POLLS = {};
  function drawPoll(c, p){
    var tot = p.options.reduce(function(s, o){ return s + o.count; }, 0);
    c.innerHTML = '<b class="t">📊 ' + esc(p.question) + "</b>" + '<div class="s">' + (p.closed ? "Voting has ended" : p.multi ? "Pick one or more" : "Pick one") + "</div>"
      + p.options.map(function(o, i){ var pc = tot ? Math.round(o.count * 100 / tot) : 0; return '<button class="xpo' + (o.mine ? " mine" : "") + '" data-vote="' + i + '"' + (p.closed ? " disabled" : "") + '><i style="width:' + pc + '%"></i><span><b>' + esc(o.text) + "</b><em>" + o.count + (tot ? " · " + pc + "%" : "") + "</em></span></button>"; }).join("")
      + '<div class="s">' + p.voters + " voted" + (p.mine_author && !p.closed ? ' · <a href="#" data-pclose>End poll</a>' : "") + "</div>";
  }
  function pollCard(el, b, id){
    var c = place(el, b, '<div class="xpc" data-poll="' + id + '"><b class="t">📊 Poll</b><div class="s">Loading…</div></div>');
    jfetch("/api/polls/" + id + "/").then(function(p){ POLLS[id] = p; drawPoll(c, p); }).catch(function(){ c.innerHTML = '<b class="t">📊 Poll</b><div class="s">This poll is not available.</div>'; });
  }
  function eventCard(el, b, iso, rest){
    var d = new Date(iso); if (isNaN(d)) return;
    var lines = rest.split("\n"), title = (lines[0] || "").replace(/^📅\s*/, ""), plc = "", note = [];
    lines.slice(1).forEach(function(l){ if (/^📍/.test(l)) plc = l.replace(/^📍\s*/, ""); else if (l.trim()) note.push(l); });
    var past = d < new Date();
    var c = place(el, b, '<div class="xpc" data-ev="' + esc(iso) + '" data-evt="' + esc(title) + '" data-evp="' + esc(plc) + '" data-evn="' + esc(note.join(" ")) + '"><b class="t">\uD83D\uDCC5 ' + esc(title) + '</b><div><b>' + esc(when(d, zone())) + '</b> <span class="s">(your time)</span></div>'
      + (plc ? '<div style="margin-top:4px">📍 ' + (/^https?:\/\//.test(plc) ? '<a href="' + esc(plc) + '" target="_blank" rel="noopener">' + esc(plc) + "</a>" : esc(plc)) + "</div>" : "")
      + (note.length ? '<div class="s" style="margin-top:4px;white-space:pre-wrap">' + esc(note.join("\n")) + "</div>" : "")
      + (past ? '<div class="s" style="margin-top:4px">This event has passed.</div>' : "")
      + '<div class="xpca"><button data-ics>📅 Add to calendar</button><button data-tz>🌍 Times</button></div><div class="xptz" hidden>' + ZONES.map(function(z){ return "<span>" + z[0] + " <b>" + esc(new Intl.DateTimeFormat("en-US", {timeZone: z[1], hour: "numeric", minute: "2-digit"}).format(d)) + "</b></span>"; }).join("") + "</div></div>");
  }
  function tile(la, lo, z){ var n = Math.pow(2, z), x = (lo + 180) / 360 * n, r = la * Math.PI / 180, y = (1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2 * n; return {x: Math.floor(x), y: Math.floor(y), fx: x % 1, fy: y % 1}; }
  function locCard(el, b, la, lo){
    var t = tile(la, lo, 15), url = "https://www.google.com/maps/search/?api=1&query=" + la + "," + lo;
    place(el, b, '<div class="xpc"><a class="xpmap" href="' + url + '" target="_blank" rel="noopener" style="background-image:url(https://tile.openstreetmap.org/15/' + t.x + "/" + t.y + '.png);background-size:256px 256px;background-position:' + Math.round(150 - t.fx * 256) + "px " + Math.round(75 - t.fy * 256) + 'px"><span class="pin" style="left:150px;top:75px">📍</span><small>© OpenStreetMap</small></a>'
      + '<b>📍 Location</b><div class="xpca"><a href="' + url + '" target="_blank" rel="noopener">🗺 Open in Maps</a><a href="https://www.openstreetmap.org/directions?to=' + la + "," + lo + '" target="_blank" rel="noopener">➡ Directions</a></div></div>');
  }
  function contactCard(el, b, slug, name){
    place(el, b, '<div class="xpc" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap"><span class="xpav">' + esc((name || "?").charAt(0)) + '</span><span style="flex:1;min-width:120px"><b>' + esc(name) + '</b><br><span class="s">XpertCreation member</span></span>'
      + '<div class="xpca" style="width:100%"><a href="/in/' + encodeURIComponent(slug) + '">👤 View profile</a></div></div>');
  }
  function cards(){
    [].forEach.call(D.querySelectorAll(BUB), function(el){
      if (el.dataset.xp) return;
      var b = bodyOf(el), t = b.text.replace(/^\s+/, ""), m;
      el.dataset.xp = "1";
      if ((m = t.match(/^\[poll:(\d+)\]/))) pollCard(el, b, m[1]);
      else if ((m = t.match(/^\[event:([0-9TZ:.\-]+)\]\s*([\s\S]*)$/))) eventCard(el, b, m[1], m[2]);
      else if ((m = t.match(/^\[loc\][\s\S]*?mlat=(-?[\d.]+)&mlon=(-?[\d.]+)/))) locCard(el, b, parseFloat(m[1]), parseFloat(m[2]));
      else if ((m = t.match(/^\[contact:([\w.\-]+)\]\s*👤\s*([^\n]*)/))) contactCard(el, b, m[1], m[2].trim());
    });
  }
  D.addEventListener("click", function(e){
    var ev = e.target.closest("[data-ev]");
    if (ev && e.target.closest("[data-ics]")){ e.preventDefault(); e.stopPropagation(); return ics(ev.dataset.evt, new Date(ev.dataset.ev), ev.dataset.evp, ev.dataset.evn); }
    if (ev && e.target.closest("[data-tz]")){ e.preventDefault(); e.stopPropagation(); var z = ev.querySelector(".xptz"); z.hidden = !z.hidden; return; }
    var v = e.target.closest("[data-vote]"), cl = e.target.closest("[data-pclose]");
    if (!v && !cl) return;
    e.preventDefault(); e.stopPropagation();
    var c = e.target.closest("[data-poll]"), id = c.dataset.poll;
    jfetch("/api/polls/" + id + "/" + (cl ? "close/" : "vote/"), cl ? {} : {option: +v.dataset.vote}).then(function(p){ POLLS[id] = p; [].forEach.call(D.querySelectorAll('[data-poll="' + id + '"]'), function(x){ drawPoll(x, p); }); }).catch(function(x){ toast(x.message); });
  }, true);
  setInterval(function(){
    if (D.hidden) return;
    [].forEach.call(D.querySelectorAll("[data-poll]"), function(c){ var r = c.getBoundingClientRect(); if (r.bottom < 0 || r.top > innerHeight) return;
      jfetch("/api/polls/" + c.dataset.poll + "/").then(function(p){ drawPoll(c, p); }).catch(function(){}); });
  }, 20000);
  var ct = null;
  new MutationObserver(function(){ clearTimeout(ct); ct = setTimeout(cards, 80); }).observe(B, {childList: true, subtree: true});
  cards();
  window.XCPLUS = {menu: menu, sendText: sendText};
})();
