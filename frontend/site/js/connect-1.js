/* Connect, Facebook-style: a "What's on your mind?" bar that opens the existing post box as a full-screen
   "Create post" sheet, with Photo / Tag people / Feeling / Check-in, @mention suggestions, and the
   "is feeling ... at ... with ..." line on posts. The feed page's own posting code is left as it is. */
(function(){
  "use strict";
  var ME = null, FEEL = null, CACHE = {}, pend = {feeling: "", feelLabel: "", place: "", tagged: [], bg: "", fg: ""};
  var BG = {blue: "linear-gradient(135deg,#1B4DFF,#7C3AED)", sunset: "linear-gradient(135deg,#F97316,#DB2777)", green: "linear-gradient(135deg,#059669,#34D399)",
            night: "linear-gradient(135deg,#0F172A,#334155)", pink: "linear-gradient(135deg,#EC4899,#F9A8D4)", gold: "linear-gradient(135deg,#F59E0B,#FDE68A)",
            sky: "linear-gradient(135deg,#0284C7,#7DD3FC)", red: "#DC2626", purple: "#7C3AED", black: "#111827", cream: "#FEF3C7", white: "#FFFFFF"};
  var FG = {white: "#FFFFFF", black: "#111827", yellow: "#FDE047", blue: "#1B4DFF"};
  function autoFg(bg){ return /^(cream|white|gold)$/.test(bg) ? "black" : "white"; }
  function esc(s){ return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function ck(n){ var x = document.cookie.match("(^|;)\\s*" + n + "\\s*=\\s*([^;]+)"); return x ? x.pop() : ""; }
  function get(u){ return fetch(u, {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; }).catch(function(){ return null; }); }
  function post(u, b){ return fetch(u, {method: "POST", credentials: "same-origin", headers: {"Content-Type": "application/json", "X-CSRFToken": ck("xc_csrf")}, body: JSON.stringify(b)}).then(function(r){ return r.json().catch(function(){ return {}; }); }); }
  var meP = get("/api/auth/me/").then(function(u){ ME = u; return u; });
  function av(u, cls){ return u && u.avatar_url ? '<img class="' + cls + '" src="' + esc(u.avatar_url) + '" alt="">' : '<span class="' + cls + '">' + esc(((u && (u.full_name || u.name)) || "?").charAt(0).toUpperCase()) + '</span>'; }

  var css = document.createElement("style");
  css.textContent = [
    /* nicer posts */
    ".fav{border-radius:50%!important}.fcard{border-radius:16px;box-shadow:0 1px 2px rgba(13,20,36,.05);padding:12px 14px}",
    ".fwho b{font-size:15px}.fbody{font-size:15.5px;line-height:1.55}.fimgs{margin-left:-14px;margin-right:-14px;border-radius:0}",
    ".facts > button{font-size:14px}.xcmeta{font-weight:400;color:var(--ink-soft,#5A657C)}.xcmeta b{color:var(--ink,#0D1424);font-weight:700}.xcmeta a{color:var(--ink,#0D1424);font-weight:700;text-decoration:none}",
    /* the bar */
    ".xcbar{display:flex;gap:10px;align-items:center;background:var(--card,#fff);border:1px solid var(--line,#E4E8F2);border-radius:16px;padding:10px 12px;margin:10px 0 12px}",
    ".xcav{width:40px;height:40px;border-radius:50%;object-fit:cover;flex:0 0 40px;background:#EEF2FF;display:grid;place-items:center;font-weight:800;color:var(--brand,#1B4DFF)}",
    ".xcopen{flex:1;text-align:left;border:1px solid var(--line,#E4E8F2);background:var(--paper,#F6F7FB);border-radius:99px;padding:11px 16px;font:inherit;font-size:15px;color:var(--ink-soft,#5A657C);cursor:pointer}",
    ".xcph{border:0;background:transparent;font-size:24px;cursor:pointer;padding:4px}",
    /* the sheet */
    ".xcsheet{display:none!important}",
    ".xcsheet.open{display:block!important;position:fixed;inset:0;z-index:300;margin:0!important;border-radius:0!important;border:0!important;overflow:auto;padding:0 16px 30px!important;background:var(--card,#fff)}",
    ".xcsh{position:sticky;top:0;background:var(--card,#fff);display:flex;align-items:center;gap:10px;padding:12px 0;border-bottom:1px solid var(--line,#E4E8F2);margin-bottom:12px;z-index:2}",
    ".xcsh b{flex:1;text-align:center;font-size:17px}.xcx{border:0;background:transparent;font-size:22px;cursor:pointer;padding:4px 8px}",
    ".xcpost{border:0;background:var(--brand,#1B4DFF);color:#fff;font:inherit;font-weight:800;padding:9px 18px;border-radius:10px;cursor:pointer}",
    ".xcwho{display:flex;gap:10px;align-items:center;margin-bottom:10px}.xcwho .xcav{width:46px;height:46px;flex-basis:46px}.xcwho b{display:block;font-size:16px}",
    ".xcwho select{margin-top:4px;padding:5px 10px;border-radius:99px;border:1px solid var(--line,#E4E8F2);background:var(--paper,#F6F7FB);font:inherit;font-size:13px;font-weight:700}",
    ".xcsum{font-size:14px;color:var(--ink-soft,#5A657C);margin-top:2px}.xcsum b{color:var(--ink,#0D1424)}",
    ".xcsheet textarea{border:0!important;font-size:19px!important;min-height:160px!important;padding:4px 0!important;outline:none;background:transparent}",
    ".xcsheet .row{display:none!important}",
    ".xcchips{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}.xcchips button{display:flex;gap:8px;align-items:center;justify-content:center;padding:12px;border-radius:12px;border:1px solid var(--line,#E4E8F2);background:var(--card,#fff);font:inherit;font-weight:700;cursor:pointer}",
    ".xcchips button.on{border-color:var(--brand,#1B4DFF);color:var(--brand,#1B4DFF);background:rgba(27,77,255,.06)}",
    "#xcpick{margin-top:12px}#xcpick input{width:100%;box-sizing:border-box;padding:11px 12px;border:1.5px solid var(--line,#E4E8F2);border-radius:12px;font:inherit}",
    ".xcgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:6px;margin-top:8px}.xcgrid button{padding:10px;border-radius:12px;border:1px solid var(--line,#E4E8F2);background:var(--card,#fff);font:inherit;font-weight:600;cursor:pointer;text-align:left}",
    ".xcgrid button.on{border-color:var(--brand,#1B4DFF);background:rgba(27,77,255,.07)}",
    ".xcpl{display:flex;gap:10px;align-items:center;padding:8px;border-radius:12px;cursor:pointer}.xcpl:hover{background:var(--paper,#F6F7FB)}.xcpl .xcav{width:36px;height:36px;flex-basis:36px}.xcpl small{display:block;color:var(--ink-soft,#5A657C)}.xcpl.on{background:rgba(27,77,255,.07)}",
    /* @mention suggestions */
    ".xcbgpost{display:flex;align-items:center;justify-content:center;text-align:center;min-height:220px;padding:28px 22px!important;margin:10px -14px 0!important;font-size:24px!important;font-weight:800;line-height:1.35!important;border-radius:0}",
    ".xcbgpost a{color:inherit!important;text-decoration:underline}",
    ".xcsw{width:40px;height:40px;border-radius:12px;border:2px solid #fff;box-shadow:0 0 0 1px var(--line,#E4E8F2);cursor:pointer;padding:0}.xcsw.on{box-shadow:0 0 0 3px var(--brand,#1B4DFF)}",
    ".xcfgb{width:34px;height:34px;border-radius:50%;border:2px solid var(--line,#E4E8F2);cursor:pointer;font-weight:800}.xcfgb.on{border-color:var(--brand,#1B4DFF);box-shadow:0 0 0 2px var(--brand,#1B4DFF)}",
    ".xcsheet textarea.xcon{text-align:center;font-weight:800!important;font-size:24px!important;min-height:240px!important;border-radius:14px;padding:30px 18px!important}",
    ".xcmen{position:absolute;z-index:400;background:var(--card,#fff);border:1px solid var(--line,#E4E8F2);border-radius:12px;box-shadow:0 12px 30px rgba(13,20,36,.18);padding:4px;min-width:220px;max-width:320px}"
  ].join("");
  document.head.appendChild(css);

  function summary(){
    var el = document.getElementById("xcsum"); if (!el) return;
    var parts = [];
    if (pend.feelLabel) parts.push("is <b>" + esc(pend.feelLabel) + "</b>");
    if (pend.place) parts.push("at <b>\uD83D\uDCCD " + esc(pend.place) + "</b>");
    if (pend.tagged.length) parts.push("with <b>" + pend.tagged.map(function(p){ return esc(p.name); }).join(", ") + "</b>");
    el.innerHTML = parts.join(" ");
    ["feel", "place", "tag"].forEach(function(k){ var b = document.querySelector('.xcchips [data-xc="' + k + '"]'); if (b) b.classList.toggle("on", k === "feel" ? !!pend.feeling : k === "place" ? !!pend.place : pend.tagged.length > 0); });
  }
  function bgPreview(){
    var ta = document.getElementById("ptext"); if (!ta) return;
    var on = !!pend.bg && ta.value.length <= 300;
    ta.classList.toggle("xcon", on);
    ta.style.background = on ? BG[pend.bg] : ""; ta.style.color = on ? FG[pend.fg || autoFg(pend.bg)] : "";
    var b = document.querySelector('.xcchips [data-xc="bg"]'); if (b) b.classList.toggle("on", !!pend.bg);
  }
  function pick(kind){
    var box = document.getElementById("xcpick"); if (!box) return;
    if (box.getAttribute("data-k") === kind){ box.innerHTML = ""; box.removeAttribute("data-k"); return; }
    box.setAttribute("data-k", kind);
    if (kind === "feel"){
      (FEEL ? Promise.resolve(FEEL) : get("/api/feedx/feelings/").then(function(d){ FEEL = (d && d.feelings) || []; return FEEL; })).then(function(list){
        box.innerHTML = '<b>How are you feeling?</b><div class="xcgrid">' + list.map(function(f){ return '<button type="button" data-feel="' + f.key + '"' + (pend.feeling === f.key ? ' class="on"' : '') + '>' + esc(f.label) + '</button>'; }).join("") + '</div>';
      });
    } else if (kind === "place"){
      box.innerHTML = '<b>Where are you?</b><div style="display:flex;gap:6px;margin-top:8px"><input id="xcplace" list="xcplist" autocomplete="off" maxlength="120" placeholder="A company on XpertConnect, or any place" value="' + esc(pend.place) + '"><datalist id="xcplist"></datalist>'
        + '<button type="button" class="xcpost" data-setplace>Add</button></div>' + (pend.place ? '<button type="button" class="xcx" style="font-size:14px" data-clearplace>Remove check-in</button>' : '');
    } else if (kind === "bg"){
      box.innerHTML = '<b>Background</b> <small style="color:var(--ink-soft)">for short text posts without a photo</small>'
        + '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px"><button type="button" class="xcsw' + (pend.bg ? '' : ' on') + '" data-bg="" style="background:#fff" title="None">\u2715</button>'
        + Object.keys(BG).map(function(k){ return '<button type="button" class="xcsw' + (pend.bg === k ? ' on' : '') + '" data-bg="' + k + '" style="background:' + BG[k] + '" title="' + k + '"></button>'; }).join("") + '</div>'
        + '<b style="display:block;margin-top:12px">Text colour</b><div style="display:flex;gap:8px;margin-top:8px">'
        + Object.keys(FG).map(function(k){ return '<button type="button" class="xcfgb' + ((pend.fg || autoFg(pend.bg)) === k ? ' on' : '') + '" data-fg="' + k + '" style="background:' + FG[k] + ';color:' + (k === "white" ? "#111" : "#fff") + '">A</button>'; }).join("") + '</div>';
    } else if (kind === "tag"){
      box.innerHTML = '<b>Tag people</b><input id="xctagq" placeholder="Search by name or @username" style="margin-top:8px"><div id="xctagl"></div>';
      tagSearch("");
    }
  }
  function tagSearch(q){
    get("/api/feedx/people/?q=" + encodeURIComponent(q)).then(function(d){
      var l = document.getElementById("xctagl"); if (!l) return;
      var list = (d && d.people) || [];
      l.innerHTML = list.length ? list.map(function(p){ var on = pend.tagged.some(function(x){ return x.id === p.id; });
        return '<div class="xcpl' + (on ? " on" : "") + '" data-tagp=\'' + esc(JSON.stringify({id: p.id, name: p.name, username: p.username})) + '\'>' + av(p, "xcav") + '<span><b>' + esc(p.name) + '</b><small>@' + esc(p.username) + (p.connected ? ' \u00b7 connection' : '') + '</small></span>' + (on ? '<span style="margin-left:auto">\u2714</span>' : '') + '</div>'; }).join("")
        : '<p class="fnote">No one found.</p>';
    });
  }
  window.XCC = {
    wrap: function(){
      var host = document.getElementById("composer"), comp = host && host.querySelector(".comp");
      if (!comp || comp.classList.contains("xcsheet")) return;
      comp.classList.add("xcsheet");
      var ta = comp.querySelector("#ptext"), vis = comp.querySelector("#pvis");
      meP.then(function(u){
        var first = ((u && u.full_name) || "").split(" ")[0] || "friend";
        var bar = document.createElement("div"); bar.className = "xcbar";
        bar.innerHTML = '<a href="/feed?user=' + ((u && u.id) || "") + '" title="My wall">' + av(u, "xcav") + '</a>' + '<button type="button" class="xcopen">What\u2019s on your mind, ' + esc(first) + '?</button><button type="button" class="xcph" aria-label="Photo">\uD83D\uDDBC\uFE0F</button>';
        host.insertBefore(bar, comp);
        var head = document.createElement("div"); head.className = "xcsh";
        head.innerHTML = '<button type="button" class="xcx" aria-label="Close">\u2715</button><b>Create post</b><button type="button" class="xcpost" data-xcpost>Post</button>';
        var who = document.createElement("div"); who.className = "xcwho";
        who.innerHTML = av(u, "xcav") + '<div><b>' + esc((u && u.full_name) || "") + '</b><div class="xcsum" id="xcsum"></div><span id="xcvis"></span></div>';
        comp.insertBefore(who, comp.firstChild); comp.insertBefore(head, comp.firstChild);
        if (vis) document.getElementById("xcvis").appendChild(vis);
        if (ta) ta.placeholder = "What\u2019s on your mind?";
        var chips = document.createElement("div"); chips.className = "xcchips";
        chips.innerHTML = '<button type="button" data-xc="photo">\uD83D\uDDBC\uFE0F Photo</button><button type="button" data-xc="tag">\uD83D\uDC65 Tag people</button>'
          + '<button type="button" data-xc="feel">\uD83D\uDE0A Feeling</button><button type="button" data-xc="place">\uD83D\uDCCD Check-in</button>'
          + '<button type="button" data-xc="bg" style="grid-column:1/-1">\uD83C\uDFA8 Background</button>';
        var prev = comp.querySelector("#prev");
        comp.insertBefore(chips, prev ? prev.nextSibling : null);
        var pk = document.createElement("div"); pk.id = "xcpick"; comp.insertBefore(pk, chips.nextSibling);
        summary();
      });
    },
    afterPost: function(id){
      var m = pend; pend = {feeling: "", feelLabel: "", place: "", tagged: [], bg: "", fg: ""};
      document.body.style.overflow = "";
      if (!m.feeling && !m.place && !m.tagged.length && !m.bg) return;
      post("/api/feedx/posts/" + id + "/meta/", {feeling: m.feeling, place: m.place, tagged: m.tagged.map(function(p){ return p.id; }), bg: m.bg, fg: m.fg}).then(function(d){
        if (d && d.meta){ CACHE[id] = d.meta; paint(id); }
      });
    },
    decorate: function(ids){
      var need = (ids || []).filter(function(i){ return !(i in CACHE); });
      var go = need.length ? get("/api/feedx/meta/?ids=" + need.join(",")).then(function(d){ need.forEach(function(i){ CACHE[i] = (d && d.meta && d.meta[i]) || null; }); }) : Promise.resolve();
      go.then(function(){ (ids || []).forEach(paint); });
    }
  };
  function paint(id){
    var m = CACHE[id], b = document.querySelector("#post-" + id + " .fwho b"); if (!b || !m) return;
    var body = document.querySelector("#post-" + id + " .fbody");
    if (body && m.bg && BG[m.bg]){ body.classList.add("xcbgpost"); body.style.background = BG[m.bg]; body.style.color = FG[m.fg] || FG[autoFg(m.bg)]; }
    var old = b.parentNode.querySelector(".xcmeta"); if (old) old.remove();
    var parts = [];
    if (m.feeling) parts.push("is <b>" + esc(m.feeling) + "</b>");
    if (m.place) parts.push('at <a href="' + (m.place_url ? esc(m.place_url) : 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(m.place)) + '"' + (m.place_url ? '' : ' target="_blank" rel="noopener"') + '><b>' + (m.place_url ? '\uD83C\uDFE2 ' : '\uD83D\uDCCD ') + esc(m.place) + '</b></a>');
    if (m.tagged && m.tagged.length) parts.push("with " + m.tagged.map(function(p){ return '<a href="/u/' + esc(p.username) + '">' + esc(p.name) + '</a>'; }).join(m.tagged.length === 2 ? " and " : ", "));
    if (!parts.length) return;
    var s = document.createElement("span"); s.className = "xcmeta"; s.innerHTML = " " + parts.join(" ");
    b.insertAdjacentElement("afterend", s);
  }
  document.addEventListener("click", function(e){
    var t = e.target;
    var sheet = document.querySelector("#composer .xcsheet");
    if (t.closest(".xcopen") || t.closest(".xcph")){
      if (sheet){ sheet.classList.add("open"); document.body.style.overflow = "hidden"; var ta = document.getElementById("ptext"); if (ta) ta.focus(); }
      if (t.closest(".xcph")){ var f = document.getElementById("pfiles"); if (f) f.click(); }
      return;
    }
    if (t.closest(".xcx") && sheet && t.closest(".xcsh")){ sheet.classList.remove("open"); document.body.style.overflow = ""; return; }
    if (t.closest("[data-xcpost]")){ var pb = document.getElementById("ppost"); if (pb) pb.click(); return; }
    var c = t.closest(".xcchips [data-xc]");
    if (c){ var k = c.getAttribute("data-xc"); if (k === "photo"){ var pf = document.getElementById("pfiles"); if (pf) pf.click(); } else pick(k); return; }
    var fb = t.closest("[data-feel]");
    if (fb){ var key = fb.getAttribute("data-feel"); if (pend.feeling === key){ pend.feeling = ""; pend.feelLabel = ""; } else { pend.feeling = key; pend.feelLabel = fb.textContent; }
      [].forEach.call(document.querySelectorAll("[data-feel]"), function(x){ x.classList.toggle("on", x.getAttribute("data-feel") === pend.feeling); }); summary(); return; }
    var sw = t.closest("[data-bg]");
    if (sw){ pend.bg = sw.getAttribute("data-bg"); if (!pend.bg) pend.fg = ""; [].forEach.call(document.querySelectorAll("[data-bg]"), function(x){ x.classList.toggle("on", x.getAttribute("data-bg") === pend.bg); });
      [].forEach.call(document.querySelectorAll("[data-fg]"), function(x){ x.classList.toggle("on", x.getAttribute("data-fg") === (pend.fg || autoFg(pend.bg))); }); bgPreview(); return; }
    var fgb = t.closest("[data-fg]");
    if (fgb){ pend.fg = fgb.getAttribute("data-fg"); [].forEach.call(document.querySelectorAll("[data-fg]"), function(x){ x.classList.toggle("on", x === fgb); }); bgPreview(); return; }
    if (t.closest("[data-setplace]")){ pend.place = (document.getElementById("xcplace").value || "").trim().slice(0, 120); summary(); pick("place"); return; }
    if (t.closest("[data-clearplace]")){ pend.place = ""; summary(); pick("place"); return; }
    var tp = t.closest("[data-tagp]");
    if (tp){ var p = JSON.parse(tp.getAttribute("data-tagp")); var i = pend.tagged.findIndex(function(x){ return x.id === p.id; });
      if (i >= 0) pend.tagged.splice(i, 1); else if (pend.tagged.length < 10) pend.tagged.push(p);
      summary(); tagSearch((document.getElementById("xctagq") || {}).value || ""); return; }
    var mp = t.closest("[data-men]");
    if (mp){ var ta2 = document.getElementById(mp.getAttribute("data-for")); if (ta2){ var pos = ta2.selectionStart, before = ta2.value.slice(0, pos).replace(/@([A-Za-z0-9_]{0,20})$/, "@" + mp.getAttribute("data-men") + " ");
        ta2.value = before + ta2.value.slice(pos); ta2.focus(); ta2.selectionStart = ta2.selectionEnd = before.length; } closeMen(); return; }
    if (!t.closest(".xcmen")) closeMen();
  });
  // @mention suggestions in the post box and in comment boxes
  var menT = null;
  function closeMen(){ var m = document.querySelector(".xcmen"); if (m) m.remove(); }
  document.addEventListener("input", function(e){
    var ta = e.target;
    if (ta.id === "ptext") bgPreview();
    if (ta.id === "xcplace"){ var pq = ta.value.trim(); clearTimeout(menT); if (pq.length < 2) return; menT = setTimeout(function(){ get("/api/companies/search/?q=" + encodeURIComponent(pq)).then(function(d){
      var dl = document.getElementById("xcplist"); if (dl) dl.innerHTML = ((d && d.companies) || []).map(function(c){ return '<option value="' + esc(c.name) + '">' + (c.verified ? "\u2714 " : "") + esc(c.city || "") + '</option>'; }).join(""); }); }, 250); return; }
    if (ta.id === "xctagq"){ clearTimeout(menT); menT = setTimeout(function(){ tagSearch(ta.value.trim()); }, 250); return; }
    if (!ta || ta.tagName !== "TEXTAREA" || !(ta.id === "ptext" || /^ctext-/.test(ta.id) || /^etext-/.test(ta.id))) return;
    var m = ta.value.slice(0, ta.selectionStart).match(/(?:^|[\s(])@([A-Za-z0-9_]{1,20})$/);
    clearTimeout(menT);
    if (!m){ closeMen(); return; }
    menT = setTimeout(function(){
      get("/api/feedx/people/?with=companies&q=" + encodeURIComponent(m[1])).then(function(d){
        var list = (d && d.people) || []; closeMen(); if (!list.length) return;
        var r = ta.getBoundingClientRect(), box = document.createElement("div"); box.className = "xcmen";
        box.style.left = (r.left + window.scrollX) + "px"; box.style.top = (r.bottom + window.scrollY + 4) + "px";
        box.innerHTML = list.slice(0, 6).map(function(p){ return '<div class="xcpl" data-men="' + esc(p.username) + '" data-for="' + ta.id + '">' + av(p, "xcav") + '<span><b>' + esc(p.name) + (p.type === "company" ? ' \uD83C\uDFE2' + (p.verified ? ' \u2714' : '') : '') + '</b><small>@' + esc(p.username) + (p.type === "company" ? ' \u00b7 company' : '') + '</small></span></div>'; }).join("");
        document.body.appendChild(box);
      });
    }, 200);
  });
})();
/* Search like Facebook: a "Search XpertConnect" pill next to the heading opens a search screen for people and hashtags. */
(function(){
  "use strict";
  function esc(s){ return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function get(u){ return fetch(u, {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; }).catch(function(){ return null; }); }
  var h1 = document.getElementById("fh1"); if (!h1 || document.getElementById("xcsrch")) return;
  var css = document.createElement("style");
  css.textContent = ".xcsrow{display:flex;align-items:center;gap:10px;justify-content:space-between;margin:6px 0 8px}.xcsrow h1{margin:0}"
    + ".xcspill{flex:0 1 280px;min-width:0;text-align:left;border:0;background:var(--paper,#EEF1F6);border-radius:99px;padding:10px 16px;font:inherit;font-size:14.5px;color:var(--ink-soft,#5A657C);cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}"
    + ".xcsearch{position:fixed;inset:0;z-index:350;background:var(--card,#fff);overflow:auto;padding:12px 16px 30px}"
    + ".xcsbar{display:flex;gap:8px;align-items:center;position:sticky;top:0;background:var(--card,#fff);padding:4px 0 10px}"
    + ".xcsbar input{flex:1;padding:12px 16px;border-radius:99px;border:0;background:var(--paper,#EEF1F6);font:inherit;font-size:16px;outline:none}"
    + ".xcsbar button{border:0;background:transparent;font-size:22px;cursor:pointer;padding:4px 8px}"
    + ".xcsh2{font-size:13px;font-weight:800;color:var(--ink-soft,#5A657C);margin:14px 4px 6px;text-transform:uppercase;letter-spacing:.04em}"
    + ".xcsr{display:flex;gap:12px;align-items:center;padding:10px 8px;border-radius:12px;text-decoration:none;color:var(--ink,#0D1424)}.xcsr:hover,.xcsr.first{background:var(--paper,#F6F7FB)}"
    + ".xcsr .ic{width:40px;height:40px;border-radius:50%;flex:0 0 40px;display:grid;place-items:center;background:#EEF2FF;color:var(--brand,#1B4DFF);font-weight:800;object-fit:cover}"
    + ".xcsr small{display:block;color:var(--ink-soft,#5A657C)}@media(max-width:520px){.xcspill span{display:none}.xcspill{flex:0 0 auto}}";
  document.head.appendChild(css);
  var old = document.getElementById("fhtag"); if (old) old.style.display = "none";
  var row = document.createElement("div"); row.className = "xcsrow";
  h1.parentNode.insertBefore(row, h1); row.appendChild(h1);
  var pill = document.createElement("button"); pill.type = "button"; pill.id = "xcsrch"; pill.className = "xcspill";
  pill.innerHTML = "\uD83D\uDD0D <span>Search XpertConnect</span>";
  row.appendChild(pill);
  var signedIn = null; get("/api/auth/me/").then(function(u){ signedIn = !!(u && u.email); });
  var TAGS = null, sheet = null, timer = null, firstHref = "";
  function open(){
    if (!sheet){
      sheet = document.createElement("div"); sheet.className = "xcsearch";
      sheet.innerHTML = '<div class="xcsbar"><button type="button" data-xcsclose aria-label="Back">\u2190</button><input id="xcsq" placeholder="Search people or #hashtags" autocomplete="off"></div><div id="xcsres"></div>';
      document.body.appendChild(sheet);
      sheet.querySelector("[data-xcsclose]").onclick = close;
      var inp = sheet.querySelector("#xcsq");
      inp.addEventListener("input", function(){ clearTimeout(timer); timer = setTimeout(function(){ run(inp.value.trim()); }, 220); });
      inp.addEventListener("keydown", function(e){ if (e.key === "Enter" && firstHref){ location.href = firstHref; } if (e.key === "Escape") close(); });
    }
    sheet.style.display = "block"; document.body.style.overflow = "hidden";
    var i = sheet.querySelector("#xcsq"); i.focus(); run(i.value.trim());
  }
  function close(){ if (sheet){ sheet.style.display = "none"; document.body.style.overflow = ""; } }
  pill.onclick = open;
  function run(q){
    var res = sheet.querySelector("#xcsres"), word = q.replace(/^[#@]/, ""), isTag = q.charAt(0) === "#";
    var tagsP = TAGS ? Promise.resolve(TAGS) : get("/api/tags/popular/").then(function(d){ TAGS = (d && d.tags) || []; return TAGS; });
    var peopleP = (!isTag && word && signedIn) ? get("/api/feedx/people/?with=companies&q=" + encodeURIComponent(word)).then(function(d){ return (d && d.people) || []; }) : Promise.resolve([]);
    Promise.all([tagsP, peopleP]).then(function(r){
      var tags = r[0].filter(function(t){ return !word || t.tag.indexOf(word.toLowerCase()) === 0; }).slice(0, word ? 6 : 10), people = r[1], h = "", hrefs = [];
      if (people.length){
        h += '<div class="xcsh2">People</div>' + people.map(function(p){ var href = p.type === "company" ? "/company/" + encodeURIComponent(p.slug) : (p.username ? "/u/" + encodeURIComponent(p.username) : "/feed?user=" + p.id); hrefs.push(href);
          return '<a class="xcsr" href="' + href + '">' + (p.avatar_url ? '<img class="ic" src="' + esc(p.avatar_url) + '" alt="">' : '<span class="ic">' + esc((p.name || "?").charAt(0)) + '</span>')
            + '<span><b>' + esc(p.name) + '</b><small>@' + esc(p.username) + (p.connected ? ' \u00b7 connection' : '') + '</small></span></a>'; }).join("");
      } else if (word && !isTag && signedIn === false){
        h += '<p class="fnote"><a href="/login">Sign in</a> to search people.</p>';
      }
      var exact = /^[A-Za-z][A-Za-z0-9_]{1,49}$/.test(word) ? word.toLowerCase() : "";
      if (exact || tags.length){
        h += '<div class="xcsh2">' + (word ? "Hashtags" : "Popular hashtags") + '</div>';
        if (exact && !tags.some(function(t){ return t.tag === exact; })){ hrefs.push("/tag/" + exact); h += '<a class="xcsr" href="/tag/' + exact + '"><span class="ic">#</span><span><b>Search #' + esc(exact) + '</b><small>Posts with this hashtag</small></span></a>'; }
        h += tags.map(function(t){ hrefs.push("/tag/" + t.tag); return '<a class="xcsr" href="/tag/' + esc(t.tag) + '"><span class="ic">#</span><span><b>#' + esc(t.tag) + '</b><small>' + t.count + ' post' + (t.count === 1 ? '' : 's') + '</small></span></a>'; }).join("");
      }
      if (!h) h = '<p class="fnote">Nothing found for \u201c' + esc(q) + '\u201d.</p>';
      res.innerHTML = h; firstHref = hrefs[0] || "";
      var f = res.querySelector(".xcsr"); if (f) f.classList.add("first");
    });
  }
})();
/* in case the feed drew its post box and posts before this script arrived */
(function(){ if (!window.XCC) return; XCC.wrap(); XCC.decorate([].map.call(document.querySelectorAll(".fcard[id^='post-']"), function(el){ return +el.id.slice(5); })); })();
/* Reactions on comments (next to Reply), and tapping any reaction count shows who reacted, with Connect. */
(function(){
  "use strict";
  var E = {like: "\uD83D\uDC4D", love: "\u2764\uFE0F", haha: "\uD83D\uDE02", wow: "\uD83D\uDE2E", sad: "\uD83D\uDE22", clap: "\uD83D\uDC4F", angry: "\uD83D\uDE21", care: "\uD83E\uDD70", celebrate: "\uD83C\uDF89"};
  var CK = ["like", "love", "haha", "wow", "sad", "clap"], C = {}, timer = null, want = {};
  function esc(s){ return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function ck(n){ var x = document.cookie.match("(^|;)\\s*" + n + "\\s*=\\s*([^;]+)"); return x ? x.pop() : ""; }
  function get(u){ return fetch(u, {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; }).catch(function(){ return null; }); }
  function post(u, b){ return fetch(u, {method: "POST", credentials: "same-origin", headers: {"Content-Type": "application/json", "X-CSRFToken": ck("xc_csrf")}, body: JSON.stringify(b || {})}).then(function(r){ return r.json().catch(function(){ return {}; }).then(function(d){ return {ok: r.ok, status: r.status, data: d}; }); }); }
  var css = document.createElement("style");
  css.textContent = ".xcrb{border:0;background:transparent;font:inherit;font-weight:700;color:var(--ink-soft,#5A657C);cursor:pointer;padding:0 4px}.xcrb.on{color:#1B4DFF}"
    + ".xcrc{border:0;background:var(--paper,#EEF1F6);border-radius:99px;padding:1px 8px;font:inherit;font-size:12.5px;cursor:pointer;margin-left:4px}"
    + ".xcrp{position:absolute;z-index:420;display:flex;gap:2px;background:var(--card,#fff);border:1px solid var(--line,#E4E8F2);border-radius:99px;box-shadow:0 10px 26px rgba(13,20,36,.18);padding:4px 6px}"
    + ".xcrp button{border:0;background:transparent;font-size:24px;cursor:pointer;padding:2px 4px;transition:transform .12s}.xcrp button:hover{transform:scale(1.25)}"
    + ".xcwhor{position:fixed;inset:0;z-index:430;background:rgba(13,20,36,.45);display:flex;align-items:flex-end;justify-content:center}"
    + ".xcwhor .bx{background:var(--card,#fff);width:100%;max-width:520px;max-height:80vh;overflow:auto;border-radius:20px 20px 0 0;padding:14px 16px 24px}@media(min-width:700px){.xcwhor{align-items:center}.xcwhor .bx{border-radius:20px}}"
    + ".xcwhor .hd{display:flex;align-items:center;gap:6px;margin-bottom:8px;position:sticky;top:-14px;background:var(--card,#fff);padding:6px 0}.xcwhor .hd b{flex:1}.xcwhor .tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px}"
    + ".xcwhor .tabs button{border:1px solid var(--line,#E4E8F2);background:var(--card,#fff);border-radius:99px;padding:6px 12px;font:inherit;font-weight:700;cursor:pointer}.xcwhor .tabs button.on{background:#1B4DFF;color:#fff;border-color:#1B4DFF}"
    + ".xcwr{display:flex;gap:10px;align-items:center;padding:8px 2px;border-top:1px solid var(--line,#E4E8F2)}.xcwr .av{position:relative;width:42px;height:42px;flex:0 0 42px}.xcwr .av img,.xcwr .av span.i{width:42px;height:42px;border-radius:50%;object-fit:cover;display:grid;place-items:center;background:#EEF2FF;color:#1B4DFF;font-weight:800}"
    + ".xcwr .av em{position:absolute;right:-4px;bottom:-4px;font-style:normal;font-size:16px}.xcwr a.n{flex:1;min-width:0;text-decoration:none;color:var(--ink,#0D1424)}.xcwr a.n small{display:block;color:var(--ink-soft,#5A657C)}"
    + ".xcwr .cn{border:0;background:#1B4DFF;color:#fff;font:inherit;font-weight:800;padding:7px 12px;border-radius:10px;cursor:pointer}.xcwr .cn[disabled]{background:var(--paper,#EEF1F6);color:var(--ink-soft,#5A657C);cursor:default}";
  document.head.appendChild(css);
  // ---- comments: add the Like button and count, in batches as comments appear
  function scan(){ [].forEach.call(document.querySelectorAll(".fcom[id^='com-']:not([data-xcr])"), function(el){ el.setAttribute("data-xcr", "1"); want[+el.id.slice(4)] = 1; }); clearTimeout(timer); timer = setTimeout(load, 120); }
  function load(){
    var ids = Object.keys(want); want = {}; if (!ids.length) return;
    get("/api/feedx/comments/counts/?ids=" + ids.join(",")).then(function(d){ var cs = (d && d.comments) || {}; ids.forEach(function(i){ C[i] = cs[i] || null; paint(i); }); });
  }
  function paint(id){
    var el = document.getElementById("com-" + id), meta = el && el.querySelector(".cmeta"), c = C[id]; if (!meta || !c) return;
    var old = meta.querySelector(".xcrw"); if (old) old.remove();
    var w = document.createElement("span"); w.className = "xcrw";
    w.innerHTML = ' \u00b7 <button type="button" class="xcrb' + (c.mine ? " on" : "") + '" data-cr="' + id + '">' + (c.mine ? E[c.mine] + " " + c.mine.charAt(0).toUpperCase() + c.mine.slice(1) : "Like") + '</button>'
      + (c.count ? '<button type="button" class="xcrc" data-crl="' + id + '">' + c.top.map(function(k){ return E[k] || ""; }).join("") + " " + c.count + '</button>' : "");
    meta.appendChild(w);
  }
  new MutationObserver(function(){ if (document.querySelector(".fcom[id^='com-']:not([data-xcr])")) scan(); }).observe(document.body, {childList: true, subtree: true});
  scan();
  function closePick(){ var p = document.querySelector(".xcrp"); if (p) p.remove(); }
  // ---- who reacted
  function who(url, title){
    get(url).then(function(d){
      var people = (d && d.people) || []; if (!people.length) return;
      var kinds = {}; people.forEach(function(p){ kinds[p.kind] = (kinds[p.kind] || 0) + 1; });
      var box = document.createElement("div"); box.className = "xcwhor";
      box.innerHTML = '<div class="bx"><div class="hd"><b>' + esc(title) + '</b><button type="button" class="xcrb" data-wclose style="font-size:22px">\u2715</button></div><div class="tabs"><button type="button" class="on" data-wt="">All ' + people.length + '</button>'
        + Object.keys(kinds).map(function(k){ return '<button type="button" data-wt="' + esc(k) + '">' + (E[k] || esc(k)) + ' ' + kinds[k] + '</button>'; }).join("") + '</div><div class="rows"></div></div>';
      document.body.appendChild(box); document.body.style.overflow = "hidden";
      function rows(f){
        box.querySelector(".rows").innerHTML = people.filter(function(p){ return !f || p.kind === f; }).map(function(p){
          var href = p.slug ? "/in/" + encodeURIComponent(p.slug) : (p.username ? "/u/" + encodeURIComponent(p.username) : "/feed?user=" + p.id);
          return '<div class="xcwr"><span class="av">' + (p.avatar_url ? '<img src="' + esc(p.avatar_url) + '" alt="">' : '<span class="i">' + esc((p.name || "?").charAt(0)) + '</span>') + '<em>' + (E[p.kind] || "") + '</em></span>'
            + '<a class="n" href="' + href + '"><b>' + esc(p.name) + '</b>' + (p.username ? '<small>@' + esc(p.username) + '</small>' : '') + '</a>'
            + (p.me ? '' : p.connected ? '<button class="cn" disabled>\u2714 Connected</button>' : (p.slug ? '<button class="cn" data-conn="' + esc(p.slug) + '">+ Connect</button>' : '')) + '</div>';
        }).join("");
      }
      rows("");
      box.addEventListener("click", function(e){
        var t = e.target;
        if (t === box || t.closest("[data-wclose]")){ box.remove(); document.body.style.overflow = ""; return; }
        var tb = t.closest("[data-wt]"); if (tb){ [].forEach.call(box.querySelectorAll("[data-wt]"), function(x){ x.classList.toggle("on", x === tb); }); rows(tb.getAttribute("data-wt")); return; }
        var cn = t.closest("[data-conn]");
        if (cn){ cn.disabled = true; post("/api/network/in/" + encodeURIComponent(cn.getAttribute("data-conn")) + "/connect/").then(function(r){ cn.textContent = r.ok ? "Request sent" : ((r.data && r.data.detail) || "Could not send"); if (r.status === 401) location.href = "/login"; }); }
      });
    });
  }
  document.addEventListener("click", function(e){
    var t = e.target;
    var b = t.closest("[data-cr]");
    if (b){
      e.preventDefault(); closePick();
      var id = b.getAttribute("data-cr"), r = b.getBoundingClientRect(), p = document.createElement("div"); p.className = "xcrp";
      p.style.left = Math.max(8, r.left + window.scrollX - 10) + "px"; p.style.top = (r.top + window.scrollY - 52) + "px";
      p.innerHTML = CK.map(function(k){ return '<button type="button" data-crk="' + k + '" data-for="' + id + '" title="' + k + '">' + E[k] + '</button>'; }).join("");
      document.body.appendChild(p); return;
    }
    var k = t.closest("[data-crk]");
    if (k){
      var cid = k.getAttribute("data-for"), kind = k.getAttribute("data-crk"), cur = C[cid] || {count: 0, top: [], mine: ""};
      var nk = cur.mine === kind ? "" : kind; closePick();
      post("/api/feedx/comments/" + cid + "/react/", {kind: nk}).then(function(r){
        if (r.status === 401 || r.status === 403){ location.href = "/login"; return; }
        if (!r.ok) return;
        cur.mine = nk; cur.count = r.data.count;
        if (nk && cur.top.indexOf(nk) < 0) cur.top.unshift(nk); if (!cur.count) cur.top = [];
        C[cid] = cur; paint(cid);
      });
      return;
    }
    if (!t.closest(".xcrp")) closePick();
    var l = t.closest("[data-crl]"); if (l){ who("/api/feedx/comments/" + l.getAttribute("data-crl") + "/reactions/", "People who reacted"); return; }
    var st = t.closest(".fstats > span");
    if (st && st.textContent.trim()){ var art = st.closest("article[id^='post-']"); if (art){ who("/api/feedx/posts/" + art.id.slice(5) + "/reactions/", "People who reacted"); } }
  });
  // the post's reaction count looks tappable
  var s2 = document.createElement("style"); s2.textContent = ".fstats > span{cursor:pointer}.fstats > span:hover{text-decoration:underline}"; document.head.appendChild(s2);
})();
/* Status (stories): a row of round photos at the top of XpertConnect, a full-screen viewer, and "Your story". */
(function(){
  "use strict";
  if (location.pathname.replace(/\/+$/, "") !== "/feed" || /[?&]user=/.test(location.search)) return;
  var BG = {blue: "linear-gradient(135deg,#1B4DFF,#7C3AED)", sunset: "linear-gradient(135deg,#F97316,#DB2777)", green: "linear-gradient(135deg,#059669,#34D399)", night: "linear-gradient(135deg,#0F172A,#334155)",
            pink: "linear-gradient(135deg,#EC4899,#F9A8D4)", gold: "linear-gradient(135deg,#F59E0B,#FDE68A)", sky: "linear-gradient(135deg,#0284C7,#7DD3FC)", red: "#DC2626", purple: "#7C3AED", black: "#111827"};
  var G = [], me = null, cur = null, timer = null;
  function esc(s){ return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function ck(n){ var x = document.cookie.match("(^|;)\\s*" + n + "\\s*=\\s*([^;]+)"); return x ? x.pop() : ""; }
  function send(u, m, body){ var h = {"X-CSRFToken": ck("xc_csrf")}; if (!(body instanceof FormData)){ h["Content-Type"] = "application/json"; body = body ? JSON.stringify(body) : undefined; }
    return fetch(u, {method: m, credentials: "same-origin", headers: h, body: body}).then(function(r){ return r.json().catch(function(){ return {}; }).then(function(d){ return {ok: r.ok, data: d}; }); }); }
  var css = document.createElement("style");
  css.textContent = ".xcst{display:flex;gap:12px;overflow-x:auto;padding:4px 2px 10px;margin:4px 0 6px;scrollbar-width:none}.xcst::-webkit-scrollbar{display:none}"
    + ".xcsi{flex:0 0 auto;width:72px;text-align:center;cursor:pointer;border:0;background:none;padding:0;font:inherit}"
    + ".xcsr{width:66px;height:66px;border-radius:50%;padding:3px;margin:0 auto 4px;background:linear-gradient(135deg,#1B4DFF,#7C3AED,#EC4899)}.xcsr.seen{background:#CBD5E1}"
    + ".xcsr span,.xcsr img{display:grid;place-items:center;width:100%;height:100%;border-radius:50%;object-fit:cover;border:3px solid var(--card,#fff);background:#EEF2FF;color:#1B4DFF;font-weight:800;font-size:22px;box-sizing:border-box}"
    + ".xcsi small{display:block;font-size:12px;color:var(--ink,#0D1424);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}"
    + ".xcsadd .xcsr{background:none;padding:0;border:2px dashed #93A4C3}.xcsadd .xcsr span{font-size:30px;border:0}"
    + ".xcsv{position:fixed;inset:0;z-index:500;background:#000;color:#fff;display:flex;flex-direction:column;user-select:none}"
    + ".xcsv .bars{display:flex;gap:4px;padding:10px 10px 6px}.xcsv .bars i{flex:1;height:3px;border-radius:2px;background:rgba(255,255,255,.35);overflow:hidden}.xcsv .bars b{display:block;height:100%;width:0;background:#fff}"
    + ".xcsv .top{display:flex;gap:10px;align-items:center;padding:4px 12px}.xcsv .top img,.xcsv .top span.a{width:36px;height:36px;border-radius:50%;object-fit:cover;background:#334;display:grid;place-items:center;font-weight:800}"
    + ".xcsv .top b{flex:1;font-size:15px}.xcsv .top small{opacity:.75;font-weight:400;margin-left:6px}.xcsv .top button{border:0;background:none;color:#fff;font-size:26px;cursor:pointer;padding:4px 8px}"
    + ".xcsv .body{flex:1;position:relative;display:flex;align-items:center;justify-content:center;overflow:hidden}.xcsv .body img{max-width:100%;max-height:100%;object-fit:contain}"
    + ".xcsv .tx{width:100%;height:100%;display:flex;align-items:center;justify-content:center;text-align:center;padding:30px;box-sizing:border-box;font-size:28px;font-weight:800;line-height:1.35;white-space:pre-wrap}"
    + ".xcsv .cap{position:absolute;bottom:16px;left:16px;right:16px;text-align:center;background:rgba(0,0,0,.45);padding:10px 12px;border-radius:12px;font-size:16px}"
    + ".xcsv .nav{position:absolute;top:0;bottom:0;width:35%;z-index:2}.xcsv .nav.l{left:0}.xcsv .nav.r{right:0}"
    + ".xcsv .foot{display:flex;gap:10px;justify-content:center;padding:12px}.xcsv .foot button{border:0;border-radius:99px;padding:10px 16px;font:inherit;font-weight:700;cursor:pointer;background:rgba(255,255,255,.15);color:#fff}"
    + ".xcsc{position:fixed;inset:0;z-index:510;background:var(--card,#fff);color:var(--ink,#0D1424);overflow:auto;padding:12px 16px 30px}"
    + ".xcsc .hd{display:flex;align-items:center;gap:10px;margin-bottom:12px}.xcsc .hd b{flex:1;font-size:18px}.xcsc .hd button{border:0;background:none;font-size:24px;cursor:pointer}"
    + ".xcsc .pick{display:grid;grid-template-columns:1fr 1fr;gap:10px}.xcsc .pick button,.xcsc .pick label{display:flex;flex-direction:column;align-items:center;gap:6px;padding:22px;border-radius:16px;border:1.5px solid var(--line,#E4E8F2);background:var(--paper,#F6F7FB);font:inherit;font-weight:800;cursor:pointer}"
    + ".xcsc .pv{border-radius:16px;overflow:hidden;background:#000;aspect-ratio:9/16;max-height:60vh;margin:0 auto 10px;display:flex;align-items:center;justify-content:center}.xcsc .pv img{max-width:100%;max-height:100%}"
    + ".xcsc textarea,.xcsc input,.xcsc select{width:100%;box-sizing:border-box;padding:11px 12px;border-radius:12px;border:1.5px solid var(--line,#E4E8F2);font:inherit;margin-bottom:10px}"
    + ".xcsc .tv{aspect-ratio:9/16;max-height:55vh;margin:0 auto 10px;border-radius:16px;display:flex;align-items:center;justify-content:center;padding:20px;box-sizing:border-box}"
    + ".xcsc .tv textarea{background:transparent;border:0;color:#fff;text-align:center;font-size:24px;font-weight:800;min-height:160px;outline:none;margin:0}.xcsc .tv textarea::placeholder{color:rgba(255,255,255,.7)}"
    + ".xcsc .dots{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;margin-bottom:12px}.xcsc .dots button{width:34px;height:34px;border-radius:50%;border:2px solid #fff;box-shadow:0 0 0 1px #CBD5E1;cursor:pointer}.xcsc .dots button.on{box-shadow:0 0 0 3px #1B4DFF}"
    + ".xcsc .go{width:100%;border:0;border-radius:14px;padding:14px;background:#1B4DFF;color:#fff;font:inherit;font-weight:800;font-size:16px;cursor:pointer}";
  document.head.appendChild(css);
  var row = document.createElement("div"); row.className = "xcst";
  function place(){ var c = document.getElementById("composer"); if (c && !row.parentNode) c.parentNode.insertBefore(row, c); }
  function av(u, cls){ return u.avatar_url ? '<img src="' + esc(u.avatar_url) + '" alt="">' : '<span class="' + (cls || "") + '">' + esc((u.name || "?").charAt(0).toUpperCase()) + '</span>'; }
  function load(){
    fetch("/api/stories/", {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; }).then(function(d){
      if (!d) return; G = d.groups || []; place();
      var mine = G.filter(function(g){ return g.mine; })[0];
      row.innerHTML = '<button class="xcsi xcsadd" data-st-new><div class="xcsr"><span>+</span></div><small>Your story</small></button>'
        + G.map(function(g, i){ return '<button class="xcsi" data-st-open="' + i + '"><div class="xcsr' + (g.seen_all ? " seen" : "") + '">' + av(g.user) + '</div><small>' + (g.mine ? "You" : esc(g.user.name.split(" ")[0])) + '</small></button>'; }).join("");
    }).catch(function(){});
  }
  function open(gi, ii){
    var g = G[gi]; if (!g) return close();
    if (ii == null){ ii = 0; for (var k = 0; k < g.items.length; k++) if (!g.items[k].seen){ ii = k; break; } }
    if (ii >= g.items.length) return open(gi + 1, 0);
    if (ii < 0) return gi > 0 ? open(gi - 1, G[gi - 1].items.length - 1) : null;
    cur = {g: gi, i: ii}; var it = g.items[ii];
    var v = document.querySelector(".xcsv") || document.body.appendChild(Object.assign(document.createElement("div"), {className: "xcsv"}));
    document.body.style.overflow = "hidden";
    v.innerHTML = '<div class="bars">' + g.items.map(function(x, k){ return '<i><b style="width:' + (k < ii ? 100 : 0) + '%"></b></i>'; }).join("") + '</div>'
      + '<div class="top">' + (g.user.avatar_url ? '<img src="' + esc(g.user.avatar_url) + '" alt="">' : '<span class="a">' + esc(g.user.name.charAt(0)) + '</span>') + '<b>' + esc(g.mine ? "Your story" : g.user.name) + '<small>' + esc(it.when) + '</small></b><button data-st-close aria-label="Close">\u2715</button></div>'
      + '<div class="body"><div class="nav l" data-st-prev></div><div class="nav r" data-st-next></div>'
      + (it.kind === "photo" ? '<img src="' + esc(it.image) + '" alt="">' + (it.text ? '<div class="cap">' + esc(it.text) + '</div>' : '') : '<div class="tx" style="background:' + (BG[it.bg] || BG.blue) + '">' + esc(it.text) + '</div>') + '</div>'
      + (g.mine ? '<div class="foot"><button data-st-viewers="' + it.id + '">\uD83D\uDC41 Seen by</button><button data-st-del="' + it.id + '">\uD83D\uDDD1 Delete</button></div>' : '');
    if (!g.mine && !it.seen){ it.seen = true; send("/api/stories/" + it.id + "/seen/", "POST", {}); }
    var bar = v.querySelectorAll(".bars b")[ii];
    clearTimeout(timer); if (bar){ bar.style.transition = "none"; bar.style.width = "0"; setTimeout(function(){ bar.style.transition = "width 5s linear"; bar.style.width = "100%"; }, 30); }
    timer = setTimeout(function(){ open(cur.g, cur.i + 1); }, 5000);
  }
  function close(){ clearTimeout(timer); var v = document.querySelector(".xcsv"); if (v) v.remove(); document.body.style.overflow = ""; cur = null; load(); }
  function creator(){
    var c = document.createElement("div"); c.className = "xcsc"; document.body.appendChild(c); document.body.style.overflow = "hidden";
    var st = {file: null, bg: "blue"};
    function hd(t){ return '<div class="hd"><button data-sc-x aria-label="Close">\u2715</button><b>' + t + '</b></div>'; }
    var aud = '<select id="xcsaud"><option value="connections">\uD83E\uDD1D My connections</option><option value="everyone">\uD83C\uDF10 Everyone</option></select>';
    function home(){ c.innerHTML = hd("Create story") + '<div class="pick"><label>\uD83D\uDCF7<span>Photo</span><input type="file" accept="image/*" id="xcsfile" hidden></label><button data-sc-text>\u270D\uFE0F<span>Text</span></button></div>'; }
    function photo(){ c.innerHTML = hd("Photo story") + '<div class="pv"><img id="xcspv" alt=""></div><input id="xcscap" maxlength="300" placeholder="Add a caption (optional)">' + aud + '<button class="go" data-sc-share>Share to your story</button><p id="xcsm" style="text-align:center"></p>';
      var r = new FileReader(); r.onload = function(){ document.getElementById("xcspv").src = r.result; }; r.readAsDataURL(st.file); }
    function text(){ c.innerHTML = hd("Text story") + '<div class="tv" id="xcstv" style="background:' + BG[st.bg] + '"><textarea id="xcstx" maxlength="300" placeholder="Type something\u2026"></textarea></div>'
      + '<div class="dots">' + Object.keys(BG).map(function(k){ return '<button data-sc-bg="' + k + '"' + (k === st.bg ? ' class="on"' : '') + ' style="background:' + BG[k] + '"></button>'; }).join("") + '</div>' + aud + '<button class="go" data-sc-share>Share to your story</button><p id="xcsm" style="text-align:center"></p>'; }
    home();
    c.addEventListener("change", function(e){ if (e.target.id === "xcsfile" && e.target.files[0]){ st.file = e.target.files[0]; photo(); } });
    c.addEventListener("click", function(e){
      var t = e.target;
      if (t.closest("[data-sc-x]")){ c.remove(); document.body.style.overflow = ""; return; }
      if (t.closest("[data-sc-text]")){ st.file = null; text(); return; }
      var b = t.closest("[data-sc-bg]"); if (b){ st.bg = b.getAttribute("data-sc-bg"); document.getElementById("xcstv").style.background = BG[st.bg]; [].forEach.call(c.querySelectorAll("[data-sc-bg]"), function(x){ x.classList.toggle("on", x === b); }); return; }
      if (t.closest("[data-sc-share]")){
        var fd = new FormData(); fd.append("audience", document.getElementById("xcsaud").value);
        if (st.file){ fd.append("image", st.file); fd.append("text", (document.getElementById("xcscap") || {}).value || ""); } else { fd.append("text", (document.getElementById("xcstx") || {}).value || ""); fd.append("bg", st.bg); }
        var m = document.getElementById("xcsm"); m.textContent = "Sharing\u2026";
        send("/api/stories/", "POST", fd).then(function(r){ if (!r.ok){ m.textContent = (r.data && r.data.detail) || "Could not share."; return; } c.remove(); document.body.style.overflow = ""; load(); });
      }
    });
  }
  document.addEventListener("click", function(e){
    var t = e.target, x;
    if (t.closest("[data-st-new]")){ creator(); return; }
    if ((x = t.closest("[data-st-open]"))){ open(+x.getAttribute("data-st-open")); return; }
    if (!document.querySelector(".xcsv")) return;
    if (t.closest("[data-st-close]")){ close(); return; }
    if (t.closest("[data-st-next]")){ open(cur.g, cur.i + 1); return; }
    if (t.closest("[data-st-prev]")){ open(cur.g, cur.i - 1); return; }
    if ((x = t.closest("[data-st-viewers]"))){
      clearTimeout(timer);
      fetch("/api/stories/" + x.getAttribute("data-st-viewers") + "/", {credentials: "same-origin"}).then(function(r){ return r.json(); }).then(function(d){
        var list = (d.viewers || []).map(function(p){ return '<div style="display:flex;gap:10px;align-items:center;padding:8px 0;border-bottom:1px solid #2a2f3a">' + (p.avatar_url ? '<img src="' + esc(p.avatar_url) + '" style="width:36px;height:36px;border-radius:50%;object-fit:cover">' : '') + '<b style="flex:1">' + esc(p.name) + '</b><small style="opacity:.7">' + esc(p.when) + '</small></div>'; }).join("") || '<p style="opacity:.7">No one yet.</p>';
        var f = document.querySelector(".xcsv .foot"); f.outerHTML = '<div class="foot" style="display:block;max-height:40vh;overflow:auto;text-align:left"><b>\uD83D\uDC41 Seen by ' + (d.viewers || []).length + '</b>' + list + '</div>';
      }); return;
    }
    if ((x = t.closest("[data-st-del]"))){ if (!confirm("Delete this story?")) return; send("/api/stories/" + x.getAttribute("data-st-del") + "/", "DELETE").then(close); }
  });
  document.addEventListener("keydown", function(e){ if (!document.querySelector(".xcsv")) return; if (e.key === "Escape") close(); if (e.key === "ArrowRight") open(cur.g, cur.i + 1); if (e.key === "ArrowLeft") open(cur.g, cur.i - 1); });
  load();
})();
