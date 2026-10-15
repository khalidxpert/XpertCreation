/* XpertConnect extras, part 2: Open to work / Hiring photo frames, polls in posts, "On this day" memories,
   birthday and work-anniversary wishes. Loaded on /feed, /post/<id>, /tag/<name> and /in/<slug>. */
(function(){
  if (window.XCSOC2) return; window.XCSOC2 = 1;
  var ME = null, PEND = null, FR = {}, AMB = {}, POLLS = {};
  function esc(s){ return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function ck(n){ var x = document.cookie.match("(^|;)\\s*" + n + "\\s*=\\s*([^;]+)"); return x ? x.pop() : ""; }
  function api(p, body){
    var o = {credentials: "same-origin", headers: {}};
    if (body !== undefined){ o.method = "POST"; o.headers["Content-Type"] = "application/json"; o.headers["X-CSRFToken"] = ck("xc_csrf"); o.body = JSON.stringify(body || {}); }
    return fetch("/api/xsocial/" + p, o).then(function(r){ return r.json().catch(function(){ return {}; }).then(function(d){ return {ok: r.ok, status: r.status, d: d}; }); })
      .catch(function(){ return {ok: false, d: {detail: "No connection. Try again."}}; });
  }
  function toast(t){ var x = document.createElement("div"); x.className = "x2-toast"; x.textContent = t; document.body.appendChild(x); setTimeout(function(){ x.remove(); }, 3000); }
  var css = document.createElement("style");
  css.textContent = ".x2-open{box-shadow:0 0 0 2px #fff,0 0 0 4.5px #16A34A!important}.x2-hire{box-shadow:0 0 0 2px #fff,0 0 0 4.5px #7C3AED!important}"
    + ".av.big.x2-open,.av.big.x2-hire{box-shadow:0 0 0 3px #fff,0 0 0 7px #16A34A!important}.av.big.x2-hire{box-shadow:0 0 0 3px #fff,0 0 0 7px #7C3AED!important}"
    + ".x2-pill{display:inline-block;margin-top:8px;padding:4px 10px;border-radius:99px;font-size:12px;font-weight:900;letter-spacing:.04em;color:#fff;background:#16A34A}.x2-pill.h{background:#7C3AED}"
    + ".x2-fbtn{display:inline-block;margin-top:8px;padding:6px 12px;border-radius:99px;border:1px solid var(--line,#E4E8F2);background:var(--card,#fff);font:inherit;font-size:12.5px;font-weight:800;cursor:pointer;color:var(--ink,#0D1424)}"
    + ".x2-poll{margin:10px 0 4px;display:grid;gap:7px}.x2-opt{position:relative;display:flex;justify-content:space-between;gap:8px;align-items:center;padding:10px 12px;border-radius:12px;border:1.5px solid var(--line,#E4E8F2);background:var(--card,#fff);font:inherit;font-size:14px;font-weight:700;cursor:pointer;text-align:left;overflow:hidden;color:var(--ink,#0D1424)}"
    + ".x2-opt i{position:absolute;left:0;top:0;bottom:0;background:#DBEAFE;z-index:0}.x2-opt span,.x2-opt b{position:relative;z-index:1}.x2-opt.me{border-color:#1B4DFF}.x2-opt.me i{background:#BFDBFE}.x2-opt[disabled]{cursor:default}"
    + ".x2-pf{font-size:12.5px;color:var(--ink-soft,#5A657C)}"
    + ".x2-box{background:var(--card,#fff);border:1px solid var(--line,#E4E8F2);border-radius:18px;padding:12px 14px;margin:0 0 12px}.x2-box b.t{display:block;font-size:14.5px;margin-bottom:8px}"
    + ".x2-mem{display:flex;gap:10px;align-items:center;padding:8px 0;border-top:1px solid var(--line,#EEF2F7);text-decoration:none;color:var(--ink,#0D1424)}.x2-mem:first-of-type{border-top:0}.x2-mem img{width:54px;height:54px;border-radius:10px;object-fit:cover}.x2-mem small{display:block;color:var(--ink-soft,#5A657C);font-weight:700}"
    + ".x2-pp{display:flex;gap:10px;align-items:center;padding:8px 0;border-top:1px solid var(--line,#EEF2F7)}.x2-pp:first-of-type{border-top:0}.x2-pp img,.x2-pp .l{width:40px;height:40px;border-radius:50%;object-fit:cover;background:#E0E7FF;display:grid;place-items:center;font-weight:800;color:#3730A3;flex:none}"
    + ".x2-pp div{flex:1;min-width:0}.x2-pp a{color:inherit;text-decoration:none;font-weight:800}.x2-pp small{display:block;color:var(--ink-soft,#5A657C)}.x2-pp button{padding:7px 12px;border-radius:99px;border:0;background:#1B4DFF;color:#fff;font:inherit;font-weight:800;font-size:13px;cursor:pointer}.x2-pp button[disabled]{background:#E2E8F0;color:#475569}"
    + ".x2-sh{position:fixed;inset:0;z-index:9005;background:rgba(13,20,36,.5);display:flex;align-items:flex-end;justify-content:center}@media(min-width:700px){.x2-sh{align-items:center}}"
    + ".x2-sh .in{background:var(--card,#fff);width:100%;max-width:480px;border-radius:20px 20px 0 0;padding:16px;font-family:inherit;color:var(--ink,#0D1424)}@media(min-width:700px){.x2-sh .in{border-radius:20px}}"
    + ".x2-sh h3{margin:0 0 10px;font-size:18px}.x2-sh input[type=text],.x2-sh textarea{width:100%;box-sizing:border-box;padding:10px 12px;border-radius:12px;border:1.5px solid var(--line,#E4E8F2);font:inherit;font-size:15px;margin-top:6px;background:var(--card,#fff);color:inherit}"
    + ".x2-sh select{padding:9px;border-radius:10px;border:1.5px solid var(--line,#E4E8F2);font:inherit;margin-top:8px}.x2-sh label.r{display:flex;gap:8px;align-items:center;padding:10px;border:1.5px solid var(--line,#E4E8F2);border-radius:12px;margin-top:8px;font-weight:700;cursor:pointer}"
    + ".x2-sh .bt{display:flex;gap:8px;margin-top:12px}.x2-sh .bt button{flex:1;padding:12px;border-radius:12px;border:0;font:inherit;font-weight:800;cursor:pointer}.x2-sh .go{background:#1B4DFF;color:#fff}.x2-sh .no{background:#F1F5F9;color:#0D1424}.x2-sh .msg{color:#B91C1C;font-size:13px;font-weight:700;margin-top:6px}"
    + ".x2-toast{position:fixed;left:50%;bottom:90px;transform:translateX(-50%);background:#0D1424;color:#fff;padding:10px 16px;border-radius:12px;font-weight:700;font-size:13.5px;z-index:9006}"
    + ".x2-amb{display:inline-block;margin:8px 6px 0 0;padding:4px 10px;border-radius:99px;font-size:12px;font-weight:900;color:#78350F;background:linear-gradient(135deg,#FDE68A,#FBBF24)}.x2-ambs{margin-left:4px;font-size:13px;text-decoration:none}"
    + ".x2-pchip{font-weight:800}.x2-pchip.on{background:#DBEAFE!important;color:#1B4DFF!important}";
  document.head.appendChild(css);
  function sheet(html){ var s = document.createElement("div"); s.className = "x2-sh"; s.innerHTML = '<div class="in">' + html + '</div>'; document.body.appendChild(s);
    s.addEventListener("click", function(e){ if (e.target === s || e.target.classList.contains("no")) s.remove(); }); return s; }

  // ---------- frames
  function paintFrames(){
    [].forEach.call(document.querySelectorAll("article.fcard[id^='post-'] .fhead"), function(h){
      var a = h.querySelector(".fwho a[href^='/in/']"), av = h.querySelector(".fav"); if (!a || !av) return;
      var s = decodeURIComponent(a.getAttribute("href").slice(4)).replace(/\/$/, ""), f = FR[s];
      av.classList.toggle("x2-open", !!(f && f.kind === "open")); av.classList.toggle("x2-hire", !!(f && f.kind === "hiring"));
      if (f) av.title = f.text;
      if (AMB[s] && !h.querySelector(".x2-ambs")){ var st = document.createElement("a"); st.className = "x2-ambs"; st.href = "/ambassadors"; st.title = "XpertCreation " + AMB[s]; st.textContent = "\u2B50"; a.insertAdjacentElement("afterend", st); }
    });
    var m = location.pathname.match(/^\/in\/([a-z0-9-]+)/i), big = document.querySelector(".av.big");
    if (m && big){
      var f = FR[m[1]];
      big.classList.toggle("x2-open", !!(f && f.kind === "open")); big.classList.toggle("x2-hire", !!(f && f.kind === "hiring"));
      var box = big.parentNode, pill = box.querySelector(".x2-pill");
      if (f && f.kind === "hiring"){ if (!pill){ pill = document.createElement("div"); big.insertAdjacentElement("afterend", pill); } pill.className = "x2-pill h"; pill.textContent = "#HIRING" + (f.text && f.text !== "Hiring" ? " · " + f.text.replace(/^Hiring:?\s*/i, "") : ""); }
      else if (pill) pill.remove();
      if (AMB[m[1]] && !box.querySelector(".x2-amb")){ var ab = document.createElement("a"); ab.className = "x2-amb"; ab.href = "/ambassadors"; ab.style.textDecoration = "none"; ab.textContent = "\u2B50 XpertCreation " + AMB[m[1]]; (box.querySelector(".x2-pill") || big).insertAdjacentElement("afterend", ab); }
      if (ME && ME.slug && ME.slug.toLowerCase() === m[1].toLowerCase() && !document.querySelector(".x2-fbtn")){
        var b = document.createElement("button"); b.type = "button"; b.className = "x2-fbtn"; b.textContent = "🖼 Photo frame";
        b.onclick = frameSheet; (box.querySelector(".x2-pill") || big).insertAdjacentElement("afterend", b);
      }
    }
  }
  var askF = {};
  function loadFrames(){
    var want = [];
    [].forEach.call(document.querySelectorAll(".fcard .fwho a[href^='/in/']"), function(a){ var s = decodeURIComponent(a.getAttribute("href").slice(4)).replace(/\/$/, ""); if (!(s in askF)){ askF[s] = 1; want.push(s); } });
    var m = location.pathname.match(/^\/in\/([a-z0-9-]+)/i); if (m && !(m[1] in askF)){ askF[m[1]] = 1; want.push(m[1]); }
    if (!want.length){ paintFrames(); return; }
    api("frames/?slugs=" + encodeURIComponent(want.slice(0, 80).join(","))).then(function(r){ var f = (r.d && r.d.frames) || {}, am = (r.d && r.d.ambassadors) || {}; Object.keys(f).forEach(function(k){ FR[k] = f[k]; }); Object.keys(am).forEach(function(k){ AMB[k] = am[k]; }); paintFrames(); });
  }
  function frameSheet(){
    api("frame/").then(function(r){
      var d = r.d || {}, k = d.kind || "";
      var s = sheet('<h3>🖼 Photo frame</h3><p class="x2-pf">A frame around your photo tells people what you are looking for. It shows on your profile and your posts.</p>'
        + [["", "No frame"], ["open", "🟢 #OpenToWork — I am looking for a job"], ["hiring", "🟣 #Hiring — I am hiring people"]].map(function(o){ return '<label class="r"><input type="radio" name="x2f" value="' + o[0] + '"' + (k === o[0] ? " checked" : "") + '> ' + o[1] + '</label>'; }).join("")
        + '<input type="text" id="x2ft" maxlength="100" placeholder="Optional: e.g. Sales jobs in Lahore / 2 graphic designers" value="' + esc(d.text || "") + '">'
        + '<div class="msg" id="x2fm"></div><div class="bt"><button class="no" type="button">Cancel</button><button class="go" type="button">Save</button></div>');
      s.querySelector(".go").onclick = function(){
        var v = (s.querySelector("input[name=x2f]:checked") || {}).value || "";
        api("frame/", {kind: v, text: s.querySelector("#x2ft").value}).then(function(x){
          if (!x.ok){ s.querySelector("#x2fm").textContent = x.d.detail || "Could not save."; return; }
          s.remove(); delete askF[ME.slug]; delete FR[ME.slug]; loadFrames(); toast(v ? "Frame saved ✓" : "Frame removed");
        });
      };
    });
  }

  // ---------- polls
  function pollHtml(id, p){
    var n = p.total, open = !p.closed && ME;
    var left = Math.max(0, Math.ceil((new Date(p.ends) - new Date()) / 864e5));
    return '<div class="x2-poll" data-poll="' + id + '">' + p.options.map(function(o, i){
      var pct = p.show && n ? Math.round((o.n || 0) * 100 / n) : 0;
      return '<button type="button" class="x2-opt' + (p.mine === i ? " me" : "") + '" data-vote="' + id + '" data-o="' + i + '"' + (open ? "" : " disabled") + '>'
        + (p.show ? '<i style="width:' + pct + '%"></i>' : '') + '<span>' + (p.mine === i ? "✓ " : "") + esc(o.t) + '</span>' + (p.show ? '<b>' + pct + '%</b>' : '') + '</button>';
    }).join("") + '<div class="x2-pf">📊 ' + n + ' vote' + (n === 1 ? "" : "s") + ' · ' + (p.closed ? "Final results" : left + " day" + (left === 1 ? "" : "s") + " left" + (p.show ? "" : " · tap a choice to see results")) + (ME ? "" : ' · <a href="/login">Sign in to vote</a>') + '</div></div>';
  }
  function paintPoll(id){
    var c = document.getElementById("post-" + id), p = POLLS[id]; if (!c || !p) return;
    var old = c.querySelector(".x2-poll"), html = pollHtml(id, p);
    if (old){ old.outerHTML = html; return; }
    var at = c.querySelector(".fbody") || c.querySelector(".fhead"); if (at) at.insertAdjacentHTML("afterend", html);
  }
  function loadPolls(ids){
    if (!ids.length) return;
    api("polls/?ids=" + ids.join(",")).then(function(r){ var ps = (r.d && r.d.polls) || {}; Object.keys(ps).forEach(function(k){ POLLS[k] = ps[k]; paintPoll(k); }); });
  }
  function pollSheet(){
    var o = PEND || {options: ["", ""], days: 7};
    var s = sheet('<h3>📊 Add a poll</h3><p class="x2-pf">Write your question as the post text. Add 2 to 4 choices.</p><div id="x2po">'
      + [0, 1, 2, 3].map(function(i){ return '<input type="text" maxlength="80" data-po="' + i + '" placeholder="Choice ' + (i + 1) + (i > 1 ? " (optional)" : "") + '" value="' + esc(o.options[i] || "") + '">'; }).join("")
      + '</div><select id="x2pd">' + [[1, "1 day"], [3, "3 days"], [7, "1 week"], [14, "2 weeks"]].map(function(d){ return '<option value="' + d[0] + '"' + (o.days === d[0] ? " selected" : "") + '>Poll runs ' + d[1] + '</option>'; }).join("") + '</select>'
      + '<div class="msg" id="x2pm"></div><div class="bt"><button class="no" type="button" id="x2prm">' + (PEND ? "Remove poll" : "Cancel") + '</button><button class="go" type="button">Add poll</button></div>');
    s.querySelector("#x2prm").onclick = function(){ PEND = null; chip(); s.remove(); };
    s.querySelector(".go").onclick = function(){
      var opts = [].map.call(s.querySelectorAll("[data-po]"), function(i){ return i.value.trim(); }).filter(Boolean);
      if (opts.length < 2){ s.querySelector("#x2pm").textContent = "Add at least 2 choices."; return; }
      PEND = {options: opts, days: +s.querySelector("#x2pd").value}; chip(); s.remove();
      var ta = document.getElementById("ptext"); if (ta && !ta.value.trim()){ ta.placeholder = "Write your poll question here"; ta.focus(); }
    };
  }
  function chip(){
    var b = document.querySelector("[data-x2poll]"); if (!b) return;
    b.classList.toggle("on", !!PEND); b.textContent = PEND ? "📊 Poll ✓ (" + PEND.options.length + ")" : "📊 Poll";
  }
  function composer(){
    var chips = document.querySelector(".xcchips");
    if (chips && !chips.querySelector("[data-x2poll]")){
      var b = document.createElement("button"); b.type = "button"; b.className = "x2-pchip"; b.setAttribute("data-x2poll", "1"); b.onclick = pollSheet;
      var bg = chips.querySelector("[data-xc=bg]"); chips.insertBefore(b, bg); chip();
    }
    if (window.XCC && XCC.afterPost && !XCC.afterPost._x2){
      var orig = XCC.afterPost;
      XCC.afterPost = function(id){
        orig.apply(this, arguments);
        if (!PEND) return;
        var m = PEND; PEND = null; chip();
        api("polls/", {post: id, options: m.options, days: m.days}).then(function(r){
          if (!r.ok){ toast(r.d.detail || "Could not add the poll."); return; }
          POLLS[id] = r.d.poll; setTimeout(function(){ paintPoll(id); }, 300);
        });
      };
      XCC.afterPost._x2 = 1;
    }
  }

  // ---------- memories and wishes (feed only)
  function feedBox(){
    if (!ME || !/^\/feed(\.html)?\/?$/.test(location.pathname) || document.getElementById("x2feed")) return;
    var list = document.getElementById("flist"); if (!list) return;
    var box = document.createElement("div"); box.id = "x2feed"; list.parentNode.insertBefore(box, list);
    Promise.all([api("memories/"), api("celebrate/")]).then(function(r){
      var mem = (r[0].d && r[0].d.memories) || [], ppl = (r[1].d && r[1].d.people) || [], h = "";
      if (mem.length) h += '<div class="x2-box"><b class="t">🕰 On this day</b>' + mem.map(function(m){
        return '<a class="x2-mem" href="/post/' + m.id + '">' + (m.image ? '<img src="' + esc(m.image) + '" alt="">' : '') + '<div><small>' + m.years + ' year' + (m.years === 1 ? "" : "s") + ' ago · ' + m.year + '</small>' + esc(m.body.slice(0, 140) || "Photo") + '</div></a>'; }).join("") + '</div>';
      if (ppl.length) h += '<div class="x2-box"><b class="t">🎉 Celebrate your connections</b>' + ppl.map(function(p){
        return '<div class="x2-pp">' + (p.avatar ? '<img src="' + esc(p.avatar) + '" alt="">' : '<span class="l">' + esc(p.name.charAt(0)) + '</span>') + '<div>'
          + (p.slug ? '<a href="/in/' + esc(p.slug) + '">' + esc(p.name) + '</a>' : '<b>' + esc(p.name) + '</b>') + '<small>' + esc(p.text) + '</small></div>'
          + '<button type="button" data-wish="' + p.id + '" data-k="' + p.kind + '" data-n="' + esc(p.name) + '"' + (p.wished ? ' disabled>Wished ✓' : '>' + (p.kind === "birthday" ? "🎂 Wish" : "👏 Congratulate")) + '</button></div>'; }).join("") + '</div>';
      box.innerHTML = h;
    });
  }
  document.addEventListener("click", function(e){
    var v = e.target.closest("[data-vote]");
    if (v && !v.disabled){
      var id = v.getAttribute("data-vote"); v.disabled = true;
      api("polls/" + id + "/vote/", {option: +v.getAttribute("data-o")}).then(function(r){ if (r.ok){ POLLS[id] = r.d.poll; paintPoll(id); } else { v.disabled = false; toast(r.d.detail || "Could not vote."); } });
      return;
    }
    var w = e.target.closest("[data-wish]");
    if (w && !w.disabled){
      var k = w.getAttribute("data-k"), n = w.getAttribute("data-n");
      var s = sheet('<h3>' + (k === "birthday" ? "🎂 Wish " : "👏 Congratulate ") + esc(n) + '</h3><textarea id="x2wt" maxlength="200" rows="3">' + (k === "birthday" ? "Happy birthday, " + esc(n.split(" ")[0]) + "! 🎂 Have a great year." : "Congratulations on your work anniversary, " + esc(n.split(" ")[0]) + "! 🎉") + '</textarea>'
        + '<div class="msg" id="x2wm"></div><div class="bt"><button class="no" type="button">Cancel</button><button class="go" type="button">Send</button></div>');
      s.querySelector(".go").onclick = function(){
        api("wish/", {to: +w.getAttribute("data-wish"), kind: k, text: s.querySelector("#x2wt").value}).then(function(r){
          if (!r.ok){ s.querySelector("#x2wm").textContent = r.d.detail || "Could not send."; return; }
          s.remove(); w.disabled = true; w.textContent = "Wished ✓"; toast("Sent ✓ They get a notification.");
        });
      };
    }
  });

  // ---------- run
  var seen = {};
  function tick(){
    var ids = [];
    [].forEach.call(document.querySelectorAll("article.fcard[id^='post-']"), function(c){
      var id = c.id.slice(5);
      if (!seen[id]){ seen[id] = 1; ids.push(id); }
      else if (POLLS[id] && !c.querySelector(".x2-poll")) paintPoll(id);     // the card was redrawn
    });
    loadPolls(ids.slice(0, 60)); loadFrames(); composer(); feedBox();
  }
  fetch("/api/xsocial/frame/", {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; }).then(function(d){ ME = d; }).catch(function(){}).then(function(){
    tick();
    var t; new MutationObserver(function(){ clearTimeout(t); t = setTimeout(tick, 200); }).observe(document.body, {childList: true, subtree: true});
  });
})();
