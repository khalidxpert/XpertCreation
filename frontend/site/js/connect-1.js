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
      box.innerHTML = '<b>Where are you?</b><div style="display:flex;gap:6px;margin-top:8px"><input id="xcplace" maxlength="120" placeholder="e.g. Gaddafi Stadium, Lahore" value="' + esc(pend.place) + '">'
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
    if (m.place) parts.push('at <a href="https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(m.place) + '" target="_blank" rel="noopener"><b>\uD83D\uDCCD ' + esc(m.place) + '</b></a>');
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
    if (ta.id === "xctagq"){ clearTimeout(menT); menT = setTimeout(function(){ tagSearch(ta.value.trim()); }, 250); return; }
    if (!ta || ta.tagName !== "TEXTAREA" || !(ta.id === "ptext" || /^ctext-/.test(ta.id) || /^etext-/.test(ta.id))) return;
    var m = ta.value.slice(0, ta.selectionStart).match(/(?:^|[\s(])@([A-Za-z0-9_]{1,20})$/);
    clearTimeout(menT);
    if (!m){ closeMen(); return; }
    menT = setTimeout(function(){
      get("/api/feedx/people/?q=" + encodeURIComponent(m[1])).then(function(d){
        var list = (d && d.people) || []; closeMen(); if (!list.length) return;
        var r = ta.getBoundingClientRect(), box = document.createElement("div"); box.className = "xcmen";
        box.style.left = (r.left + window.scrollX) + "px"; box.style.top = (r.bottom + window.scrollY + 4) + "px";
        box.innerHTML = list.slice(0, 6).map(function(p){ return '<div class="xcpl" data-men="' + esc(p.username) + '" data-for="' + ta.id + '">' + av(p, "xcav") + '<span><b>' + esc(p.name) + '</b><small>@' + esc(p.username) + '</small></span></div>'; }).join("");
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
    var peopleP = (!isTag && word && signedIn) ? get("/api/feedx/people/?q=" + encodeURIComponent(word)).then(function(d){ return (d && d.people) || []; }) : Promise.resolve([]);
    Promise.all([tagsP, peopleP]).then(function(r){
      var tags = r[0].filter(function(t){ return !word || t.tag.indexOf(word.toLowerCase()) === 0; }).slice(0, word ? 6 : 10), people = r[1], h = "", hrefs = [];
      if (people.length){
        h += '<div class="xcsh2">People</div>' + people.map(function(p){ var href = p.username ? "/u/" + encodeURIComponent(p.username) : "/feed?user=" + p.id; hrefs.push(href);
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
