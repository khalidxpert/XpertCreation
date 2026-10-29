/* XpertConnect v1 (setup_xconnect_v1): post reshare + a personal analytics view on /feed#analytics.
   Loaded only on the feed page. The reshare button is added by feed.html; the click is handled here,
   and the whole analytics screen is built here so feed.html stays small. */
(function(){
  "use strict";
  if (window.XCONN) return; window.XCONN = 1;
  function ck(n){ var x = document.cookie.match("(^|;)\\s*" + n + "\\s*=\\s*([^;]+)"); return x ? x.pop() : ""; }
  function esc(s){ return String(s == null ? "" : s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }
  function api(p, o){
    o = o || {};
    var h = {"Accept": "application/json"};
    if (o.method && o.method !== "GET"){ h["Content-Type"] = "application/json"; h["X-CSRFToken"] = ck("xc_csrf"); }
    return fetch("/api/feed" + p, {method: o.method || "GET", headers: h, credentials: "same-origin",
                                   body: o.body ? JSON.stringify(o.body) : undefined})
      .then(function(r){ return r.json().catch(function(){ return {}; }).then(function(d){ return {ok: r.ok, data: d}; }); })
      .catch(function(){ return {ok: false, data: {}}; });
  }

  /* ---------- reshare ---------- */
  document.addEventListener("click", function(e){
    var t = e.target.closest ? e.target.closest("[data-reshare]") : null;
    if (!t) return;
    e.preventDefault();
    var id = t.getAttribute("data-reshare");
    if (t.dataset.busy) return; t.dataset.busy = "1";
    api("/posts/" + id + "/reshare/", {method: "POST"}).then(function(r){
      t.dataset.busy = "";
      if (!r.ok) return;
      t.classList.toggle("on", !!r.data.reshared);
      t.innerHTML = "🔁 " + (r.data.reshares ? r.data.reshares : "Reshare");
      try { if (window.posts && window.posts[id]){ window.posts[id].reshares = r.data.reshares; window.posts[id].reshared = r.data.reshared; } } catch (err) {}
    });
  });

  /* ---------- analytics ---------- */
  var CSS = ""
    + ".xca{margin:4px 0 20px}"
    + ".xca h2{font-size:19px;font-weight:900;margin:0 0 4px}"
    + ".xca .sub{color:var(--ink-soft,#5A657C);font-size:13px;margin:0 0 14px}"
    + ".xca .chartc{background:var(--card,#fff);border:1px solid var(--line,#E4E8F2);border-radius:16px;padding:14px 14px 8px;margin-bottom:14px}"
    + ".xca .chartc b{font-size:13px;color:var(--ink-soft,#5A657C);font-weight:800;letter-spacing:.02em}"
    + ".xca svg{display:block;width:100%;height:150px;margin-top:6px}"
    + ".xca .grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px}"
    + ".xca .tile{background:var(--card,#fff);border:1px solid var(--line,#E4E8F2);border-radius:16px;padding:14px 16px;display:flex;align-items:center;gap:12px}"
    + ".xca .tile .ic{width:44px;height:44px;border-radius:13px;display:grid;place-items:center;font-size:22px;flex:0 0 44px}"
    + ".xca .tile .v{font-size:24px;font-weight:900;line-height:1.05}"
    + ".xca .tile .k{font-size:12.5px;color:var(--ink-soft,#5A657C);font-weight:600}"
    + ".xca .eng{background:linear-gradient(100deg,#1B4DFF,#7C3AED);color:#fff;border-radius:16px;padding:16px 18px;display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}"
    + ".xca .eng .l{font-size:15px;font-weight:800;display:flex;align-items:center;gap:9px}.xca .eng .r{font-size:26px;font-weight:900}"
    + ".xca .wk{background:var(--card,#fff);border:1px solid var(--line,#E4E8F2);border-radius:16px;padding:14px 16px}"
    + ".xca .wk h3{font-size:15px;font-weight:800;margin:0 0 12px}"
    + ".xca .row{display:grid;grid-template-columns:92px 1fr 44px;align-items:center;gap:10px;margin-bottom:11px}"
    + ".xca .row .nm{font-size:13.5px;color:var(--ink-soft,#5A657C);font-weight:600}"
    + ".xca .row .ba{height:9px;border-radius:99px;background:var(--paper,#F1F5F9);overflow:hidden}"
    + ".xca .row .ba i{display:block;height:100%;border-radius:99px}"
    + ".xca .row .nn{font-size:14px;font-weight:800;text-align:right}"
    + ".xca .empty{color:var(--ink-soft,#5A657C);font-size:13.5px;padding:8px 2px}";
  var TILES = [
    ["posts","Posts","📝","#EEF2FF","#1B4DFF"],
    ["impressions","Impressions","👁️","#E0F2FE","#0284C7"],
    ["likes","Likes","❤️","#FEE2E2","#DC2626"],
    ["comments","Comments","💬","#EDE9FE","#7C3AED"],
    ["reshares","Reshares","🔁","#DCFCE7","#059669"],
    ["followers","Followers","👥","#FEF3C7","#D97706"]
  ];
  var injected = false, box = null;
  function ensure(){
    if (injected) return;
    injected = true;
    var st = document.createElement("style"); st.textContent = CSS; document.head.appendChild(st);
    box = document.createElement("div"); box.id = "xcanalytics"; box.className = "xca"; box.style.display = "none";
    var anchor = document.getElementById("fmore") || document.getElementById("flist");
    if (anchor && anchor.parentNode) anchor.parentNode.insertBefore(box, anchor.nextSibling);
    else document.querySelector(".feedw, main, body").appendChild(box);
  }
  function lineChart(series){
    var w = 600, h = 150, pad = 22, n = series.length;
    var max = 1; series.forEach(function(p){ if (p.n > max) max = p.n; });
    var dx = (w - pad * 2) / (n - 1 || 1);
    function X(i){ return pad + dx * i; }
    function Y(v){ return h - pad - (h - pad * 2) * (v / max); }
    var pts = series.map(function(p, i){ return X(i) + "," + Y(p.n); });
    var area = "M" + X(0) + "," + (h - pad) + " L" + pts.join(" L") + " L" + X(n - 1) + "," + (h - pad) + " Z";
    var line = "M" + pts.join(" L");
    var labs = "";
    [0, Math.floor(n / 2), n - 1].forEach(function(i){
      labs += '<text x="' + X(i) + '" y="' + (h - 5) + '" font-size="10" fill="#8aa0cc" text-anchor="middle">' + esc(series[i].d) + '</text>';
    });
    return '<svg viewBox="0 0 ' + w + ' ' + h + '" preserveAspectRatio="none">'
      + '<defs><linearGradient id="xcg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1B4DFF" stop-opacity=".22"/><stop offset="1" stop-color="#1B4DFF" stop-opacity="0"/></linearGradient></defs>'
      + '<path d="' + area + '" fill="url(#xcg)"/>'
      + '<path d="' + line + '" fill="none" stroke="#1B4DFF" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>'
      + labs + '</svg>';
  }
  function wkRow(nm, v, max, color){
    var pct = max ? Math.round(v * 100 / max) : 0;
    return '<div class="row"><span class="nm">' + esc(nm) + '</span><span class="ba"><i style="width:' + pct + '%;background:' + color + '"></i></span><span class="nn">' + v + '</span></div>';
  }
  function render(d){
    ensure();
    var tt = d.totals || {}, wk = d.week || {}, series = d.series || [];
    var tiles = TILES.map(function(x){
      return '<div class="tile"><span class="ic" style="background:' + x[3] + ';color:' + x[4] + '">' + x[2] + '</span>'
        + '<span><span class="v">' + (tt[x[0]] || 0) + '</span><br><span class="k">' + x[1] + '</span></span></div>';
    }).join("");
    var wkmax = Math.max(wk.likes || 0, wk.comments || 0, wk.reshares || 0, wk.followers || 0, 1);
    var wkrows = wkRow("Likes", wk.likes || 0, wkmax, "#DC2626")
      + wkRow("Comments", wk.comments || 0, wkmax, "#7C3AED")
      + wkRow("Reshares", wk.reshares || 0, wkmax, "#059669")
      + wkRow("New followers", wk.followers || 0, wkmax, "#1B4DFF");
    box.innerHTML = '<h2>Your analytics</h2><p class="sub">How your posts are doing on XpertConnect.</p>'
      + '<div class="chartc"><b>IMPRESSIONS · LAST 14 DAYS</b>' + lineChart(series) + '</div>'
      + '<div class="grid">' + tiles + '</div>'
      + '<div class="eng"><span class="l">📈 Engagement rate</span><span class="r">' + (tt.engagement || 0) + '%</span></div>'
      + '<div class="wk"><h3>This week’s activity</h3>' + wkrows + '</div>';
  }
  function show(on){
    ensure();
    var ids = ["composer", "ftabs", "flist", "fmore", "fhtag"];
    ids.forEach(function(i){ var el = document.getElementById(i); if (el) el.style.display = on ? "none" : ""; });
    box.style.display = on ? "" : "none";
    var hub = document.querySelector(".hubbar");
    if (hub) Array.prototype.forEach.call(hub.querySelectorAll("a"), function(a){
      a.classList.toggle("on", on ? /#analytics$/.test(a.getAttribute("href") || "") : (a.getAttribute("href") === "/feed"));
    });
    if (on){
      box.innerHTML = '<p class="sub" style="padding:18px 2px">Loading your analytics…</p>';
      api("/analytics/").then(function(r){
        if (r.ok) render(r.data);
        else box.innerHTML = '<p class="empty">' + ((r.data && r.data.detail) || "Sign in to see your analytics.") + '</p>';
      });
    }
  }
  function route(){ show(location.hash.replace(/^#/, "") === "analytics"); }
  function addLink(){
    var hub = document.querySelector(".hubbar");
    if (hub && !hub.querySelector('a[href="#analytics"]')){
      var a = document.createElement("a"); a.href = "#analytics"; a.textContent = "Analytics"; hub.appendChild(a);
    }
  }
  function start(){ addLink(); route(); window.addEventListener("hashchange", route); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
