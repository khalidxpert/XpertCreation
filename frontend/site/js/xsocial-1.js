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
    + ".x3-sec{margin-top:14px}.x3-sec h2{display:flex;align-items:center;gap:8px;justify-content:space-between}.x3-sec h2 button,.x3-btn{padding:7px 12px;border-radius:10px;border:1px solid var(--line,#E4E8F2);background:var(--card,#fff);font:inherit;font-size:13px;font-weight:800;cursor:pointer;color:var(--ink,#0D1424)}"
    + ".x3-btn.p{background:#1B4DFF;border-color:#1B4DFF;color:#fff}.x3-feat{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px}"
    + ".x3-fc{position:relative;display:block;border:1px solid var(--line,#E4E8F2);border-radius:14px;overflow:hidden;background:var(--card,#fff);text-decoration:none;color:var(--ink,#0D1424)}"
    + ".x3-fc img{width:100%;height:110px;object-fit:cover;display:block}.x3-fc div{padding:10px 12px}.x3-fc b{display:block;font-size:14px;line-height:1.35}.x3-fc small{display:block;color:var(--ink-soft,#5A657C);font-size:12.5px;margin-top:4px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}"
    + ".x3-fc .k{font-size:11px;font-weight:900;color:#1B4DFF;letter-spacing:.04em}.x3-fc .rm{position:absolute;top:6px;right:6px;border:0;background:rgba(255,255,255,.95);border-radius:8px;padding:3px 7px;font-weight:800;cursor:pointer}"
    + ".x3-rec{border-top:1px solid var(--line,#EEF2F7);padding:12px 0}.x3-rec:first-of-type{border-top:0}.x3-rec .h{display:flex;gap:10px;align-items:center}.x3-rec .h img,.x3-rec .h .l{width:40px;height:40px;border-radius:50%;object-fit:cover;background:#E0E7FF;display:grid;place-items:center;font-weight:800;color:#3730A3}"
    + ".x3-rec .h a{color:inherit;font-weight:800;text-decoration:none}.x3-rec .h small{display:block;color:var(--ink-soft,#5A657C)}.x3-rec p{margin:8px 0 0;white-space:pre-wrap;line-height:1.55;font-size:14.5px}.x3-rec .bt{display:flex;gap:6px;margin-top:8px}"
    + ".x3-art{display:flex;gap:10px;border-top:1px solid var(--line,#EEF2F7);padding:10px 0;text-decoration:none;color:var(--ink,#0D1424)}.x3-art:first-of-type{border-top:0}.x3-art img{width:80px;height:56px;border-radius:8px;object-fit:cover}.x3-art small{display:block;color:var(--ink-soft,#5A657C)}"
    + ".x3-stars{color:#F59E0B;letter-spacing:1px}.x3-pick button{font-size:30px;border:0;background:none;cursor:pointer;color:#CBD5E1;padding:0 2px}.x3-pick button.on{color:#F59E0B}"
    + ".x3-bar{display:flex;align-items:center;gap:6px;font-size:12.5px}.x3-bar i{flex:1;height:8px;border-radius:9px;background:#EEF2F7;position:relative;overflow:hidden}.x3-bar i b{position:absolute;left:0;top:0;bottom:0;background:#F59E0B}"
    + ".x3-reply{margin-top:8px;padding:8px 10px;border-radius:10px;background:var(--paper,#F6F7FB);font-size:13.5px}"
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
      var mem = (r[0].d && r[0].d.memories) || [], ppl = (r[1].d && r[1].d.people) || [];
      var h = '<div class="x2-box" style="display:flex;gap:8px;flex-wrap:wrap;padding:10px 12px">' + [["/events", "📅 Events"], ["/articles", "📰 Articles"], ["/ambassadors", "⭐ Ambassadors"], ["/safety", "🛡️ Safety"]].map(function(l){
        return '<a href="' + l[0] + '" style="padding:7px 12px;border-radius:99px;background:var(--paper,#F1F5F9);text-decoration:none;color:var(--ink,#0D1424);font-weight:800;font-size:13px">' + l[1] + '</a>'; }).join("") + '</div>';
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


  // ---------- step 2: close friends audience, profile and post menus (block / mute / restrict / close friends)
  function audience(){
    var sel = document.getElementById("pvis");
    if (sel && !sel.querySelector('option[value="close"]')){ var o = document.createElement("option"); o.value = "close"; o.textContent = "⭐ Close friends"; sel.appendChild(o); }
  }
  function relSheet(slug, name){
    api("rel/?slug=" + encodeURIComponent(slug)).then(function(r){
      if (!r.ok || r.d.me) return;
      var d = r.d, first = esc((name || "this person").split(" ")[0]);
      var row = function(act, on, label, sub){ return '<label class="r" style="justify-content:space-between"><span><b>' + label + '</b><br><span class="x2-pf">' + sub + '</span></span><input type="checkbox" data-rel="' + act + '"' + (on ? " checked" : "") + '></label>'; };
      var s = sheet('<h3>' + esc(name || "") + '</h3>'
        + row("close", d.close, "⭐ Close friend", "Sees your posts shared with Close friends")
        + row("mute", d.mute, "🔇 Mute", "Hide " + first + "'s posts from your feed. They are not told.")
        + row("restrict", d.restrict, "🔒 Restrict", first + "'s new comments on your posts are seen only by them and you")
        + row("block", d.block, "🚫 Block", "You can't see each other's profile or posts, or message. Your connection ends.")
        + '<div class="msg" id="x2rm"></div><div class="bt"><button class="no" type="button">Close</button></div>');
      s.addEventListener("change", function(e){
        var c = e.target.closest("[data-rel]"); if (!c) return;
        var act = c.getAttribute("data-rel");
        if (act === "block" && c.checked && !confirm("Block " + (name || "this person") + "?")){ c.checked = false; return; }
        api("people/" + act + "/", {slug: slug, on: c.checked}).then(function(x){
          if (!x.ok){ c.checked = !c.checked; s.querySelector("#x2rm").textContent = x.d.detail || "Could not save."; return; }
          toast({close: c.checked ? "Added to Close friends" : "Removed from Close friends", mute: c.checked ? "Muted" : "Unmuted", restrict: c.checked ? "Restricted" : "Not restricted", block: c.checked ? "Blocked" : "Unblocked"}[act]);
          if (act === "block" && c.checked){ setTimeout(function(){ location.href = "/feed"; }, 900); }
        });
      });
    });
  }
  function profileMenu(){
    var m = location.pathname.match(/^\/in\/([a-z0-9-]+)/i), acts = document.querySelector(".acts");
    if (!m || !acts || !ME || acts.querySelector(".x2-more") || (ME.slug && ME.slug.toLowerCase() === m[1].toLowerCase())) return;
    var b = document.createElement("button"); b.className = "btn x2-more"; b.type = "button"; b.textContent = "⋯ More";
    b.onclick = function(){ relSheet(m[1], ((document.querySelector("h1") || {}).textContent || "").replace(/\s*Verified\s*$/, "")); }; acts.appendChild(b);
  }
  document.addEventListener("click", function(e){
    var t = e.target.closest("[data-menu]");
    if (t && ME){
      setTimeout(function(){
        var id = t.getAttribute("data-menu"), mb = document.getElementById("menu-" + id), card = document.getElementById("post-" + id);
        if (!mb || !mb.innerHTML || mb.querySelector("[data-x2rel]") || !mb.querySelector("[data-preport]")) return;
        var a = card && card.querySelector(".fwho a[href^='/in/']"); if (!a) return;
        var slug = decodeURIComponent(a.getAttribute("href").slice(4)).replace(/\/$/, ""), nm = a.textContent.trim();
        mb.insertAdjacentHTML("beforeend", '<button type="button" data-x2rel="' + esc(slug) + '" data-n="' + esc(nm) + '">🔇 Mute / 🚫 Block…</button>');
      }, 30);
      return;
    }
    var r = e.target.closest("[data-x2rel]"); if (r) relSheet(r.getAttribute("data-x2rel"), r.getAttribute("data-n"));
  });


  // ---------- step 3: profile sections (featured, recommendations, articles), company reviews
  function stars(n){ var s = ""; for (var i = 1; i <= 5; i++) s += i <= Math.round(n) ? "★" : "☆"; return '<span class="x3-stars">' + s + '</span>'; }
  function av(p){ return p.avatar ? '<img src="' + esc(p.avatar) + '" alt="">' : '<span class="l">' + esc((p.name || "?").charAt(0)) + '</span>'; }
  function day(t){ return new Date(t).toLocaleDateString("en-GB", {day: "numeric", month: "short", year: "numeric"}); }
  var PSLUG = null, PBOX = null;
  function profileSections(){
    var m = location.pathname.match(/^\/in\/([a-z0-9-]+)/i); if (!m) return;
    var head = document.querySelector(".acts"); head = head && head.closest(".card"); if (!head) return;
    if (document.getElementById("x3prof")) return;
    PSLUG = m[1]; PBOX = document.createElement("div"); PBOX.id = "x3prof"; head.insertAdjacentElement("afterend", PBOX);
    PBOX.innerHTML = '<div id="x3feat"></div><div id="x3recs"></div><div id="x3arts"></div>';
    loadFeat(); loadRecs(); loadArts();
  }
  function loadFeat(){
    api("featured/?slug=" + PSLUG).then(function(r){
      var d = r.d || {}, it = d.items || [], el = document.getElementById("x3feat"); if (!el) return;
      if (!it.length && !d.mine){ el.innerHTML = ""; return; }
      el.innerHTML = '<div class="x3-sec"><h2>⭐ Featured' + (d.mine && it.length < 6 ? ' <button type="button" id="x3fadd">+ Add a link</button>' : '') + '</h2>'
        + (it.length ? '<div class="x3-feat">' + it.map(function(f){ return '<a class="x3-fc" href="' + esc(f.url) + '"' + (f.kind === "link" ? ' target="_blank" rel="noopener"' : '') + '>'
          + (d.mine ? '<button class="rm" type="button" data-x3fdel="' + f.id + '" title="Remove">✕</button>' : '') + (f.image ? '<img src="' + esc(f.image) + '" alt="" loading="lazy">' : '')
          + '<div><span class="k">' + (f.kind === "post" ? "POST" : "LINK") + '</span><b>' + esc(f.title) + '</b>' + (f.note ? '<small>' + esc(f.note) + '</small>' : '') + '</div></a>'; }).join("") + '</div>'
          : '<div class="card" style="color:var(--ink-soft,#5A657C);font-size:14px">Show your best work here: tap ⋯ on one of your posts and choose 📌 Feature, or add a link (portfolio, video, website).</div>') + '</div>';
    });
  }
  function loadRecs(){
    api("recs/?slug=" + PSLUG).then(function(r){
      var d = r.d || {}, el = document.getElementById("x3recs"); if (!el) return;
      var sh = d.shown || [], pend = d.pending || [];
      if (!sh.length && !pend.length && !d.can_write){ el.innerHTML = ""; return; }
      var one = function(x, act){ return '<div class="x3-rec"><div class="h">' + av(x.by) + '<div>' + (x.by.slug ? '<a href="/in/' + esc(x.by.slug) + '">' + esc(x.by.name) + '</a>' : '<b>' + esc(x.by.name) + '</b>')
        + '<small>' + esc(x.relation || x.by.headline || "") + ' · ' + day(x.when) + '</small></div></div><p>' + esc(x.body) + '</p>' + (act ? '<div class="bt">' + act(x) + '</div>' : '') + '</div>'; };
      el.innerHTML = '<div class="x3-sec" id="recs"><h2>💬 Recommendations' + (sh.length ? ' (' + sh.length + ')' : '') + (d.can_write ? ' <button type="button" id="x3rwrite">✍️ Recommend</button>' : '') + '</h2>'
        + (pend.length ? '<div class="card" style="border-color:#FCD34D;background:#FFFBEB"><b>Waiting for you (' + pend.length + ')</b>' + pend.map(function(x){ return one(x, function(y){ return '<button class="x3-btn p" data-x3rec="show" data-id="' + y.id + '">Show on my profile</button><button class="x3-btn" data-x3rec="delete" data-id="' + y.id + '">Delete</button>'; }); }).join("") + '</div>' : '')
        + (sh.length ? '<div class="card">' + sh.map(function(x){ return one(x, d.mine ? function(y){ return '<button class="x3-btn" data-x3rec="hide" data-id="' + y.id + '">Hide</button>'; } : null); }).join("") + '</div>'
          : (d.can_write ? '<div class="card" style="color:var(--ink-soft,#5A657C);font-size:14px">No recommendations yet. Worked with them? Write one.</div>' : '')) + '</div>';
    });
  }
  function loadArts(){
    Promise.all([api("articles/?by=" + PSLUG), api("subscribe/?slug=" + PSLUG)]).then(function(r){
      var a = (r[0].d && r[0].d.articles) || [], s = r[1].d || {}, el = document.getElementById("x3arts"); if (!el) return;
      if (!a.length && !s.me){ el.innerHTML = ""; return; }
      el.innerHTML = '<div class="x3-sec"><h2>📰 Articles' + (a.length ? ' (' + a.length + ')' : '')
        + (s.me ? ' <a class="x3-btn" href="/articles#new" style="text-decoration:none">✍️ Write</a>' : (ME ? ' <button type="button" class="x3-btn' + (s.on ? '' : ' p') + '" id="x3sub" data-on="' + (s.on ? 0 : 1) + '">' + (s.on ? "✓ Subscribed" : "🔔 Subscribe") + '</button>' : '')) + '</h2>'
        + '<div class="card">' + (s.count ? '<div style="font-size:13px;color:var(--ink-soft,#5A657C);margin-bottom:6px">' + s.count + ' subscriber' + (s.count === 1 ? "" : "s") + '</div>' : '')
        + (a.length ? a.slice(0, 5).map(function(x){ return '<a class="x3-art" href="/articles#a' + x.id + '">' + (x.cover ? '<img src="' + esc(x.cover) + '" alt="">' : '') + '<div><b>' + esc(x.title) + '</b><small>' + day(x.when) + ' · ' + x.minutes + ' min read</small></div></a>'; }).join("")
          : '<div style="color:var(--ink-soft,#5A657C);font-size:14px">Write long posts that people can subscribe to. <a href="/articles#new">Write your first article</a>.</div>') + '</div></div>';
    });
  }
  var CSLUG = null;
  function companyReviews(){
    var m = location.pathname.match(/^\/company\/([a-z0-9-]+)/); if (!m || document.getElementById("x3crev")) return;
    var posts = document.getElementById("cpposts"); if (!posts) return;
    CSLUG = m[1]; var box = document.createElement("div"); box.className = "cpbox"; box.id = "x3crev"; posts.closest(".cpbox").insertAdjacentElement("afterend", box); loadCrev();
  }
  var PICK = 0;
  function loadCrev(){
    api("coreviews/?slug=" + CSLUG).then(function(r){
      var d = r.d || {}, box = document.getElementById("x3crev"); if (!box || !r.ok) return;
      var mine = (d.reviews || []).filter(function(x){ return x.mine; })[0];
      var h = '<h2 id="reviews" style="display:flex;justify-content:space-between;align-items:center">Reviews <span style="font-size:14px">' + (d.count ? stars(d.avg) + ' <b>' + d.avg + '</b> (' + d.count + ')' : '') + '</span></h2>';
      if (d.count) h += [5, 4, 3, 2, 1].map(function(i){ var n = d.dist[i] || 0; return '<div class="x3-bar">' + i + '★<i><b style="width:' + Math.round(n * 100 / d.count) + '%"></b></i>' + n + '</div>'; }).join("");
      if (d.can_review){ PICK = mine ? mine.stars : 0;
        h += '<div style="margin:12px 0;padding:12px;border-radius:12px;background:var(--paper,#F6F7FB)"><b>' + (mine ? "Your review" : "Write a review") + '</b><div class="x3-pick" id="x3pick">' + [1, 2, 3, 4, 5].map(function(i){ return '<button type="button" data-st="' + i + '" class="' + (i <= PICK ? "on" : "") + '">★</button>'; }).join("") + '</div>'
          + '<textarea id="x3rb" rows="3" maxlength="1500" placeholder="How was your experience?" style="width:100%;box-sizing:border-box;padding:10px;border-radius:10px;border:1.5px solid var(--line,#E4E8F2);font:inherit">' + esc(mine ? mine.body : "") + '</textarea>'
          + '<button class="x3-btn p" id="x3rgo" style="margin-top:6px">' + (mine ? "Update" : "Post review") + '</button> <span id="x3rm" style="font-size:13px;font-weight:700;color:#B91C1C"></span></div>'; }
      else if (!d.signed) h += '<p style="font-size:14px"><a href="/login?next=' + encodeURIComponent(location.pathname) + '">Sign in</a> to write a review.</p>';
      h += (d.reviews || []).map(function(x){ return '<div class="x3-rec"><div class="h">' + av(x.by) + '<div>' + (x.by.slug ? '<a href="/in/' + esc(x.by.slug) + '">' + esc(x.by.name) + '</a>' : '<b>' + esc(x.by.name) + '</b>') + '<small>' + stars(x.stars) + ' · ' + day(x.when) + (x.hidden ? ' · hidden' : '') + '</small></div></div>'
        + (x.body ? '<p>' + esc(x.body) + '</p>' : '') + (x.reply ? '<div class="x3-reply"><b>Reply from the business:</b> ' + esc(x.reply) + '</div>' : '')
        + '<div class="bt">' + (d.owner ? '<button class="x3-btn" data-crev="reply" data-id="' + x.id + '">' + (x.reply ? "Edit reply" : "Reply") + '</button><button class="x3-btn" data-crev="report" data-id="' + x.id + '">Report</button>' : '')
        + (x.mine ? '<button class="x3-btn" data-crev="delete" data-id="' + x.id + '">Delete</button>' : '') + (d.staff ? '<button class="x3-btn" data-crev="' + (x.hidden ? "unhide" : "hide") + '" data-id="' + x.id + '">' + (x.hidden ? "Unhide" : "Hide") + '</button>' : '') + '</div></div>'; }).join("")
        || '<p style="color:var(--ink-soft,#5A657C);font-size:14px">No reviews yet.</p>';
      box.innerHTML = h;
      if (location.hash === "#reviews") box.scrollIntoView();
    });
  }
  document.addEventListener("click", function(e){
    var t = e.target;
    if (t.id === "x3fadd"){
      var s = sheet('<h3>⭐ Add a featured link</h3><input type="text" id="x3fu" placeholder="https://… (portfolio, video, website)"><input type="text" id="x3ft" maxlength="120" placeholder="Title"><input type="text" id="x3fn" maxlength="200" placeholder="Short note (optional)"><div class="msg" id="x3fm"></div><div class="bt"><button class="no" type="button">Cancel</button><button class="go" type="button">Add</button></div>');
      s.querySelector(".go").onclick = function(){ api("featured/", {url: s.querySelector("#x3fu").value, title: s.querySelector("#x3ft").value, note: s.querySelector("#x3fn").value}).then(function(r){ if (!r.ok){ s.querySelector("#x3fm").textContent = r.d.detail || "Could not add."; return; } s.remove(); loadFeat(); }); };
      return;
    }
    var fd = t.closest("[data-x3fdel]"); if (fd){ e.preventDefault(); api("featured/" + fd.getAttribute("data-x3fdel") + "/remove/", {}).then(loadFeat); return; }
    var ff = t.closest("[data-x3feat]"); if (ff){ api("featured/", {post: +ff.getAttribute("data-x3feat")}).then(function(r){ toast(r.ok ? "📌 Featured on your profile" : (r.d.detail || "Could not feature.")); }); return; }
    if (t.id === "x3rwrite"){
      var s2 = sheet('<h3>✍️ Write a recommendation</h3><p class="x2-pf">It shows on their profile after they accept it.</p><input type="text" id="x3rr" maxlength="120" placeholder="How you know them, e.g. Worked together at ABC"><textarea id="x3rt" rows="5" maxlength="1500" placeholder="What are they great at? What was it like to work with them?"></textarea><div class="msg" id="x3rmm"></div><div class="bt"><button class="no" type="button">Cancel</button><button class="go" type="button">Send</button></div>');
      s2.querySelector(".go").onclick = function(){ api("recs/", {slug: PSLUG, relation: s2.querySelector("#x3rr").value, body: s2.querySelector("#x3rt").value}).then(function(r){ if (!r.ok){ s2.querySelector("#x3rmm").textContent = r.d.detail || "Could not send."; return; } s2.remove(); toast("Sent ✓ It shows after they accept."); loadRecs(); }); };
      return;
    }
    var rc = t.closest("[data-x3rec]"); if (rc){ api("recs/" + rc.getAttribute("data-id") + "/" + rc.getAttribute("data-x3rec") + "/", {}).then(loadRecs); return; }
    if (t.id === "x3sub"){ api("subscribe/", {slug: PSLUG, on: t.getAttribute("data-on") === "1"}).then(function(r){ if (r.ok){ toast(r.d.on ? "🔔 Subscribed. You'll get a notification for new articles." : "Unsubscribed"); loadArts(); } }); return; }
    var st = t.closest("[data-st]"); if (st){ PICK = +st.getAttribute("data-st"); [].forEach.call(document.querySelectorAll("#x3pick button"), function(b){ b.classList.toggle("on", +b.getAttribute("data-st") <= PICK); }); return; }
    if (t.id === "x3rgo"){ api("coreviews/", {slug: CSLUG, stars: PICK, body: document.getElementById("x3rb").value}).then(function(r){ if (r.ok) loadCrev(); else document.getElementById("x3rm").textContent = r.d.detail || "Could not post."; }); return; }
    var cr = t.closest("[data-crev]");
    if (cr){ var act = cr.getAttribute("data-crev"), id = cr.getAttribute("data-id"), body = {};
      if (act === "reply"){ body.reply = prompt("Your public reply:"); if (body.reply === null) return; }
      if (act === "report"){ body.why = prompt("What is wrong with this review? Our team will look at it."); if (!body.why) return; }
      if (act === "delete" && !confirm("Delete this review?")) return;
      api("coreviews/" + id + "/" + act + "/", body).then(function(r){ if (act === "report") toast("Thanks. Our team will look at it."); loadCrev(); }); }
  });
  document.addEventListener("click", function(e){        // 📌 Feature, in the menu of your own post
    var t = e.target.closest("[data-menu]"); if (!t) return;
    setTimeout(function(){ var id = t.getAttribute("data-menu"), mb = document.getElementById("menu-" + id);
      if (mb && mb.innerHTML && mb.querySelector("[data-edit]") && !mb.querySelector("[data-x3feat]")) mb.insertAdjacentHTML("beforeend", '<button type="button" data-x3feat="' + id + '">📌 Feature on my profile</button>'); }, 40);
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
    loadPolls(ids.slice(0, 60)); loadFrames(); composer(); feedBox(); audience(); profileMenu(); profileSections(); companyReviews();
  }
  fetch("/api/xsocial/frame/", {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; }).then(function(d){ ME = d; }).catch(function(){}).then(function(){
    tick();
    var t; new MutationObserver(function(){ clearTimeout(t); t = setTimeout(tick, 200); }).observe(document.body, {childList: true, subtree: true});
  });
})();
